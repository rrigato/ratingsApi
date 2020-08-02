
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import json
import os
import requests
import unittest


class ShowsUnitTests(unittest.TestCase):
    """Testing shows endpoint logic unit tests only

        Parameters
        ----------

        Returns
        -------

        Raises
        ------
    """
    @classmethod
    def setUpClass(cls):
        """Unitest function that is run once for the class

            Parameters
            ----------

            Returns
            -------

            Raises
            ------
        """
        pass


    @patch("microservices.shows.shows.get_boto_clients")
    def test_main(self, get_boto_clients_mock):
        '''Test for main function

            Parameters
            ----------
            ratings_iteration_mock : unittest.mock.MagicMock
                Mock object to make sure the reddit api is 
                not called

            handle_ratings_iteration_mock : unittest.mock.MagicMock
                Mock object used to ensure no logging is setup
                for the test

            Returns
            -------

            Raises
            ------
        '''
        from microservices.shows.shows import main

        apigw_response = main()


        self.assertEqual(type(apigw_response["body"]), str)

        self.assertEqual(apigw_response["statusCode"], 200 )



    @patch("boto3.client")
    def test_get_boto_clients_no_region(self, boto3_client_mock):
        '''Tests outgoing boto3 client generation when no region is passed

            Parameters
            ----------
            boto3_client_mock : unittest.mock.MagicMock
                Mock object used to patch
                AWS Python SDK

            Returns
            -------


            Raises
            ------
        '''
        from microservices.shows.shows import get_boto_clients

        test_service_name="lambda"
        get_boto_clients(resource_name=test_service_name)


        '''
            Default region is us-east-1 for 
            get_boto_clients
        '''
        boto3_client_mock.assert_called_once_with(
            service_name=test_service_name,
            region_name="us-east-1"
        )
    def test_get_boto_clients_table_resource(self):
        """Tests getting a dynamodb table resource from get_boto_clients

            Parameters
            ----------

            Returns
            -------


            Raises
            ------
        """
        from microservices.shows.shows import get_boto_clients

        dynamodb_functions_to_test = [
            "put_item",
            "query",
            "scan"
        ]
        '''
            boto3 does not make any calls to 
            aws until you use the resource/client
        '''
        test_service_name = "dynamodb"
        test_table_name = "fake_ddb_table"

        dynamodb_client, dynamodb_table = get_boto_clients(
            resource_name=test_service_name, 
            table_name=test_table_name
        )


        '''
            Testing the objects returned have the needed functions
        '''
        self.assertIn(
            "describe_table",
            dir(dynamodb_client)
        )

        '''
            ensuring we have all needed functions for
            working with a table
        '''
        for dynamodb_function in dynamodb_functions_to_test:
            self.assertIn(
                dynamodb_function,
                dir(dynamodb_table)
            )        


    @patch("microservices.shows.shows.get_boto_clients")
    def test_dynamodb_show_request(self, get_boto_clients_mock):
        """tests dynamodb_show_request is called with the correct arguements

            Parameters
            ----------
            get_boto_clients_mock : Mocks the get_boto_clients call
            Returns
            -------

            Raises
            ------
        """
        from microservices.shows.shows import dynamodb_show_request
        from boto3.dynamodb.conditions import Key

        mock_dynamodb_resource = MagicMock()
        
        '''
            return None for client, mock for dynamodb table resource
        '''
        get_boto_clients_mock.return_value = (None, mock_dynamodb_resource)
        
        mock_show_name = "mock_show"
        dynamodb_show_request(show_name=mock_show_name)

        mock_dynamodb_resource.query.assert_called_once_with(
            IndexName="SHOW_ACCESS",
            KeyConditionExpression=Key("SHOW").eq(mock_show_name)
        )