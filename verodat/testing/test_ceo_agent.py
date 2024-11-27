"""
This unit test file is designed to test the functionality of the CEOAgent class, specifically its get_value_proposition method.

Test Setup:
- Adds the parent directory to the PYTHONPATH to ensure that the verodat module can be imported.
- Imports the unittest module for creating and running tests.
- Imports the MagicMock class from unittest.mock for creating mock objects.
- Imports the CEOAgent class to be tested.
- Imports the VerodatAgent class to be mocked.
- The setUp method runs before each test, creating a mock VerodatAgent and an instance of CEOAgent using the mock.

Test Cases:
1. test_get_value_proposition_success:
   - Mocks the responses from VerodatAgent to return a mock dataset info dictionary and a mock dataset output list.
   - Calls the get_value_proposition method of CEOAgent and asserts that the actual value proposition matches the expected value.

2. test_get_value_proposition_failure:
   - Mocks the response from VerodatAgent to return None to simulate a failure.
   - Calls the get_value_proposition method of CEOAgent and asserts that the actual value proposition matches the expected failure message.

These tests ensure that the CEOAgent behaves as expected in both success and failure scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import MagicMock
from verodat.agent_ceo import CEOAgent
from verodat.agent_value_prop import VerodatAgent

class TestCEOAgent(unittest.TestCase):
    def setUp(self):
        # Mock the VerodatAgent
        self.mock_verodat_agent = MagicMock(spec=VerodatAgent)
        self.ceo_agent = CEOAgent(self.mock_verodat_agent)

    def test_get_value_proposition_success(self):
        # Mock the responses from VerodatAgent
        self.mock_verodat_agent.get_dataset_info.return_value = {
            'name': 'Test Dataset',
            'version': {'version': '1.0'}
        }
        self.mock_verodat_agent.retrieve_data_from_dataset.return_value = {
            'output': [{'id': 1}, {'id': 2}, {'id': 3}]
        }

        # Call the method and check the result
        value_proposition = self.ceo_agent.get_value_proposition()
        expected_value_proposition = (
            "Dataset Name: Test Dataset\n"
            "Dataset Version: 1.0\n"
            "Data Summary: The dataset contains 3 records.\n"
        )
        self.assertEqual(value_proposition, expected_value_proposition)

    def test_get_value_proposition_failure(self):
        # Mock the responses from VerodatAgent
        self.mock_verodat_agent.get_dataset_info.return_value = None

        # Call the method and check the result
        value_proposition = self.ceo_agent.get_value_proposition()
        self.assertEqual(value_proposition, "Failed to retrieve dataset information.")

if __name__ == '__main__':
    unittest.main()