import logging
import os
from typing import List, Optional, Sequence, Tuple

from chromadb.api.types import EmbeddingFunction
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.conversions.common_types import ScoredPoint
from qdrant_client.http.models import (
    Batch,
    CollectionStatus,
    Distance,
    Filter,
    SearchParams,
    VectorParams,
)

from langroid.embedding_models.base import (
    EmbeddingModel,
    EmbeddingModelsConfig,
)
from langroid.mytypes import Document
from langroid.utils.configuration import settings
from langroid.vector_store.base import VectorStore, VectorStoreConfig

logger = logging.getLogger(__name__)


class QdrantDBConfig(VectorStoreConfig):
    type: str = "qdrant"
    cloud: bool = True

    collection_name: str | None = None
    storage_path: str = ".qdrant/data"
    embedding: EmbeddingModelsConfig = EmbeddingModelsConfig(
        model_type="openai",
    )
    distance: str = Distance.COSINE


class QdrantDB(VectorStore):
    def __init__(self, config: QdrantDBConfig):
        super().__init__(config)
        self.config = config
        emb_model = EmbeddingModel.create(config.embedding)
        self.embedding_fn: EmbeddingFunction = emb_model.embedding_fn()
        self.embedding_dim = emb_model.embedding_dims
        self.host = config.host
        self.port = config.port
        load_dotenv()
        if config.cloud:
            key = os.getenv("QDRANT_API_KEY")
            url = os.getenv("QDRANT_API_URL")
            if key is None or key == "" or url is None or url == "":
                raise ValueError(
                    """QDRANT_API_KEY, QDRANT_API_URL env variable must be set to use 
                    QdrantDB in cloud mode. Please set these values 
                    in your .env file.
                    """
                )
            self.client = QdrantClient(
                url=url,
                api_key=key,
                timeout=config.timeout,
            )
        else:
            self.client = QdrantClient(
                path=config.storage_path,
            )

        # Note: Only create collection if a non-null collection name is provided.
        # This is useful to delay creation of vecdb until we have a suitable
        # collection name (e.g. we could get it from the url or folder path).
        if config.collection_name is not None:
            self.create_collection(
                config.collection_name, replace=config.replace_collection
            )

    def clear_empty_collections(self) -> int:
        coll_names = self.list_collections()
        n_deletes = 0
        for name in coll_names:
            info = self.client.get_collection(collection_name=name)
            if info.points_count == 0:
                n_deletes += 1
                self.client.delete_collection(collection_name=name)
        return n_deletes

    def _list_all_collections(self) -> List[str]:
        """
        List all collections, including empty ones.
        Returns:
            List of collection names.
        """
        colls = list(self.client.get_collections())[0][1]
        return [coll.name for coll in colls]

    def list_collections(self) -> List[str]:
        """
        Returns:
            List of collection names that have at least one vector.
        """
        colls = list(self.client.get_collections())[0][1]
        counts = [
            self.client.get_collection(collection_name=coll.name).points_count
            for coll in colls
        ]
        return [coll.name for coll, count in zip(colls, counts) if count > 0]

    def create_collection(self, collection_name: str, replace: bool = False) -> None:
        """
        Create a collection with the given name, optionally replacing an existing
            collection if `replace` is True.
        Args:
            collection_name (str): Name of the collection to create.
            replace (bool): Whether to replace an existing collection
                with the same name. Defaults to False.
        """
        self.config.collection_name = collection_name
        collections = self.list_collections()
        if collection_name in collections:
            coll = self.client.get_collection(collection_name=collection_name)
            if coll.status == CollectionStatus.GREEN and coll.points_count > 0:
                logger.warning(f"Non-empty Collection {collection_name} already exists")
                if not replace:
                    logger.warning("Not replacing collection")
                    return
                else:
                    logger.warning("Recreating fresh collection")
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE,
            ),
        )
        collection_info = self.client.get_collection(collection_name=collection_name)
        assert collection_info.status == CollectionStatus.GREEN
        assert collection_info.vectors_count == 0
        if settings.debug:
            level = logger.getEffectiveLevel()
            logger.setLevel(logging.INFO)
            logger.info(collection_info)
            logger.setLevel(level)

    def add_documents(self, documents: Sequence[Document]) -> None:
        colls = self._list_all_collections()
        if len(documents) == 0:
            return
        embedding_vecs = self.embedding_fn([doc.content for doc in documents])
        if self.config.collection_name is None:
            raise ValueError("No collection name set, cannot ingest docs")
        if self.config.collection_name not in colls:
            self.create_collection(self.config.collection_name, replace=True)
        ids = [d.id() for d in documents]
        # don't insert all at once, batch in chunks of b,
        # else we get an API error
        b = self.config.batch_size
        for i in range(0, len(ids), b):
            self.client.upsert(
                collection_name=self.config.collection_name,
                points=Batch(
                    ids=ids[i : i + b],
                    vectors=embedding_vecs[i : i + b],
                    payloads=documents[i : i + b],
                ),
            )

    def delete_collection(self, collection_name: str) -> None:
        self.client.delete_collection(collection_name=collection_name)

    def _to_int_or_uuid(self, id: str) -> int | str:
        try:
            return int(id)
        except ValueError:
            return id

    def get_documents_by_ids(self, ids: List[str]) -> List[Document]:
        if self.config.collection_name is None:
            raise ValueError("No collection name set, cannot retrieve docs")
        _ids = [self._to_int_or_uuid(id) for id in ids]
        records = self.client.retrieve(
            collection_name=self.config.collection_name,
            ids=_ids,
            with_vectors=False,
            with_payload=True,
        )
        docs = [Document(**record.payload) for record in records]  # type: ignore
        return docs

    def similar_texts_with_scores(
        self,
        text: str,
        k: int = 1,
        where: Optional[str] = None,
    ) -> List[Tuple[Document, float]]:
        embedding = self.embedding_fn([text])[0]
        # TODO filter may not work yet
        filter = Filter() if where is None else Filter.from_json(where)  # type: ignore
        if self.config.collection_name is None:
            raise ValueError("No collection name set, cannot search")
        search_result: List[ScoredPoint] = self.client.search(
            collection_name=self.config.collection_name,
            query_vector=embedding,
            query_filter=filter,
            limit=k,
            search_params=SearchParams(
                hnsw_ef=128,
                exact=False,  # use Apx NN, not exact NN
            ),
        )
        scores = [match.score for match in search_result]
        docs = [
            Document(**(match.payload))  # type: ignore
            for match in search_result
            if match is not None
        ]
        if len(docs) == 0:
            logger.warning(f"No matches found for {text}")
            return []
        if settings.debug:
            logger.info(f"Found {len(docs)} matches, max score: {max(scores)}")
        doc_score_pairs = list(zip(docs, scores))
        self.show_if_debug(doc_score_pairs)
        return doc_score_pairs
