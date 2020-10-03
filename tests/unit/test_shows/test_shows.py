
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import json
import os
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
        with open("tests/events/shows_proxy_event.json", "r") as lambda_event:
            cls.shows_proxy_event = json.load(lambda_event)

    @patch("microservices.shows.shows.dynamodb_show_request")
    @patch("microservices.shows.shows.get_boto_clients")
    def test_main(self, get_boto_clients_mock, dynamodb_show_request_mock):
        '''Test for main function

            Parameters
            ----------
            ratings_iteration_mock : unittest.mock.MagicMock
                Mock object to make sure the reddit api is 
                not called

            dynamodb_show_request_mock : unittest.mock.MagicMock
                Mock returning the dynamodb show request

            Returns
            -------

            Raises
            ------
        '''
        from microservices.shows.shows import main

        dynamodb_show_request_mock.return_value = [None, {"statusCode": 200, "body": "{}"}]
        apigw_response = main(event=self.shows_proxy_event)


        self.assertEqual(type(apigw_response["body"]), str)

        self.assertEqual(apigw_response["statusCode"], 200 )

        dynamodb_show_request_mock.assert_called_once_with(
            show_name="mockpathparam"
        )


    @patch("microservices.shows.shows.dynamodb_show_request")
    @patch("microservices.shows.shows.get_boto_clients")
    def test_main_request_error(self, get_boto_clients_mock, dynamodb_show_request_mock):
        '''Test for main function

            Parameters
            ----------
            ratings_iteration_mock : unittest.mock.MagicMock
                Mock object to make sure the reddit api is 
                not called

            dynamodb_show_request_mock : unittest.mock.MagicMock
                Mock returning the dynamodb show request

            Returns
            -------

            Raises
            ------
        '''
        from microservices.shows.shows import main

        '''
            show parameter is not passed
        '''
        bad_request_missing_show_parameter = main(
            event={}
        )

        self.assertEqual(
            json.loads(bad_request_missing_show_parameter["body"])["message"],
            "Path parameter show is required"
        )

        self.assertEqual(bad_request_missing_show_parameter["statusCode"], 400)

        '''
            Test invalid show parameter
        '''
        bad_request_invalid_show_parameter = main(
            event={"pathParameters": {"show": "mockParameter" * 100}}
        )

        self.assertEqual(
            json.loads(bad_request_invalid_show_parameter["body"])["message"],
            "Invalid show path parameter"
        )

        self.assertEqual(bad_request_invalid_show_parameter["statusCode"], 400)


    @patch("microservices.shows.shows.dynamodb_show_request")
    @patch("microservices.shows.shows.get_boto_clients")
    def test_main_404_error(self, get_boto_clients_mock, dynamodb_show_request_mock):
        '''Test for 404 show not found error

            Parameters
            ----------
            ratings_iteration_mock : unittest.mock.MagicMock
                Mock object to make sure the reddit api is 
                not called

            dynamodb_show_request_mock : unittest.mock.MagicMock
                Mock returning the dynamodb show request

            Returns
            -------

            Raises
            ------
        '''
        from microservices.shows.shows import main

        dynamodb_show_request_mock.return_value = [
            {"message": "show: mockpathparam not found"}, []
        ]
        
        apigw_response = main(event=self.shows_proxy_event)


        self.assertEqual(
            apigw_response["body"], 
            json.dumps(
                {"message": "show: mockpathparam not found"}
            )
        )

        self.assertEqual(apigw_response["statusCode"], 404 )

        dynamodb_show_request_mock.assert_called_once_with(
            show_name="mockpathparam"
        )



    def test_clean_path_parameter_string(self):
        '''validates clean_show_path_parameter logic

            Parameters
            ----------

            Returns
            -------

            Raises
            ------
        '''
        from microservices.shows.shows import clean_path_parameter_string

        self.assertFalse(clean_path_parameter_string(show_name="a" * 501))
        self.assertTrue(clean_path_parameter_string(show_name="A show with & and ; and '"))

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

        valid_show_response = {
            "Items": [{"TOTAL_VIEWERS": "727", "PERCENTAGE_OF_HOUSEHOLDS": "0.50", "YEAR": Decimal("2013"), "SHOW": "Star Wars the Clone Wars", "TIME": "3:00", "RATINGS_OCCURRED_ON": "2013-08-17"}, {"TOTAL_VIEWERS": "683", "PERCENTAGE_OF_HOUSEHOLDS": "0.60", "YEAR": Decimal("2013"), "SHOW": "Star Wars the Clone Wars", "TIME": "3:00", "RATINGS_OCCURRED_ON": "2013-08-24"}, {"TOTAL_VIEWERS": "638", "YEAR": Decimal("2013"), "SHOW": "Star Wars the Clone Wars", "TIME": "2:45", "RATINGS_OCCURRED_ON": "2013-08-31"}],
            "Count": 0, 
            "ScannedCount": 0, 
            "ResponseMetadata": {}
        }
        mock_dynamodb_resource.query.return_value = valid_show_response

        '''
            return None for client, mock for dynamodb table resource
        '''
        get_boto_clients_mock.return_value = (None, mock_dynamodb_resource)
        
        mock_show_name = "mock_show"


        error_message, dyanmodb_shows = dynamodb_show_request(show_name=mock_show_name)

        mock_dynamodb_resource.query.assert_called_once_with(
            IndexName="SHOW_ACCESS",
            KeyConditionExpression=Key("SHOW").eq(mock_show_name)
        )


    @patch("microservices.shows.shows.get_boto_clients")
    def test_dynamodb_show_request_404(self, get_boto_clients_mock):
        """tests dynamodb_show_request for no show match http 404

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

        mock_dynamodb_resource.query.return_value = {
            "Items": [], 
            "Count": 0, 
            "ScannedCount": 0, 
            "ResponseMetadata": {}
        }

        error_message, dyanmodb_shows = dynamodb_show_request(show_name=mock_show_name)

        self.assertEqual(error_message, {
            "message": "show: {show_name} not found".format(
                show_name=mock_show_name
                )
            }
        )
        self.assertEqual(dyanmodb_shows, [])


    @patch("logging.getLogger")
    @patch("microservices.shows.shows.main")
    def test_lambda_handler_event(self, main_mock, 
        getLogger_mock):
        """Tests passing sample event to lambda_handler

            Parameters
            ----------
            main_mock : unittest.mock.MagicMock
                Mock object used to patch the main function

            getLogger_mock : unittest.mock.MagicMock
                Mock object used to patch get_logger for lambda handler

            Returns
            -------

            Raises
            ------
        """
        from microservices.shows.shows import lambda_handler

        lambda_handler(
            event=self.shows_proxy_event,
            context={}
        )

        self.assertEqual(
            getLogger_mock.call_count,
            1
        )

        '''
            Testing call count and args passed
        '''
        main_mock.assert_called_once_with(
            event=self.shows_proxy_event
        )
