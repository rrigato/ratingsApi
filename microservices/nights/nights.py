import boto3
import json
import logging
import os

from boto3.dynamodb.conditions import Key
from datetime import datetime
from microlib.microlib import get_boto_clients
from microlib.microlib import lambda_proxy_response


def clean_path_parameter_string(night):
    """Validates the night path parameter

        Parameters
        ----------
        night : str
            night passed to the request, must be in YYYY-MM-DD
            format

        Returns
        -------
        valid_night : boolean
            True if night is valid in YYYY-MM-DD
            format False otherwise
            
        Raises
        ------
    """
    if type(night) != str:
        logging.info("clean_path_parameter_string - datatype")
        return(False)    
    if len(night) > 10:
        logging.info("clean_path_parameter_string - string length")
        return(False)
    try:
        valid_date_format = datetime.strptime(night, "%Y-%m-%d")        

    except ValueError:
        logging.info("clean_path_parameter_string - Invalid date format")
        return(False)    

    return(True)


def validate_request_parameters(event):
    """Validates the request passed in via the lambda handler event

        Parameters
        ----------
        event : dict
            lambda_handler event from api gateway

        Returns
        -------
        error_response : dict
            None if request is valid. Otherwise a dict with 
            keys status_code and message detailing the error in
            the request

        Raises
        ------
    """
    error_response = None
    try:
        assert clean_path_parameter_string(event["pathParameters"]["night"]) is True, (
            "night parameter invalid"
        )
        logging.info("validate_request_parameters - night parameter valid")

    except KeyError:
        logging.info("validate_request_parameters - night parameter not found in request")
        error_response = {
            "message": "Path parameter night is required",
            "status_code": 400 
        }

    except AssertionError:
        logging.info("validate_request_parameters - night parameter invalid")
        error_response = {
            "message": "Invalid night path parameter, must be in YYYY-MM-DD format",
            "status_code": 404 
        }

    return(error_response)

def dynamodb_night_request(night):
    """Query using the night_ACCESS GSI

        Parameters
        ----------
        night : str
            night passed to the request, must be in YYYY-MM-DD
            format

        Returns
        -------
        error_message : dict
            None if items are returned, dict of 404 errors otherwise
        show_ratings : list
            list of dict where each dict is a television show
            rating

        Raises
        ------
    """
    error_message = None

    if os.environ.get("DYNAMO_TABLE_NAME") is None:
        dynamo_table_name = "prod_toonami_ratings"
    else:
        dynamo_table_name = os.environ.get("DYNAMO_TABLE_NAME")

    logging.info("dynamodb_night_request - DYNAMO_TABLE_NAME" + dynamo_table_name)
    dynamo_client, dynamo_table = get_boto_clients(
            resource_name="dynamodb",
            region_name="us-east-1",
            table_name=dynamo_table_name
    )

    logging.info("dynamodb_night_request - Access table through PK" )

    '''
        Query one night using the PK RATINGS_OCCURRED_ON
    '''
    ratings_query_response = dynamo_table.query(
        KeyConditionExpression=Key("RATINGS_OCCURRED_ON").eq(night)
    )

    show_ratings = ratings_query_response["Items"]
    logging.info("dynamodb_night_request - Count " + str(ratings_query_response["Count"]))

    '''
        If no items returned
    '''
    if ratings_query_response["Count"] == 0:
        error_message = {
            "message": "night: {night_number} not found".format(
                night_number=night
            )
        }
    else:
        logging.info("dynamodb_night_request - preparing night for serialization")
        '''
            convert from decimal to str for json serialization
        '''
        for individual_show in show_ratings:
            try:
                individual_show["YEAR"] = str(individual_show["YEAR"])
            except KeyError:
                logging.info("dynamodb_night_request - No YEAR for " + individual_show["SHOW"])
        
    logging.info(error_message)

    return(error_message, show_ratings)


def main(event):
    """Entry point into the script

        Parameters
        ----------
        event : dict
            api gateway lambda proxy event

        Returns
        -------

        Raises
        ------
    """
    error_response = validate_request_parameters(event=event)

    if error_response is not None:
        status_code = error_response.pop("status_code")
        '''
            return http 400 level error response
        '''
        return(lambda_proxy_response(status_code=status_code, 
        headers_dict={}, response_body=error_response))


    error_message, ratings_query_response = dynamodb_night_request(
        night=event["pathParameters"]["night"]
    )

    if error_message is None:
        logging.info("main - returning ratings_query_response" + str(len(ratings_query_response)))
        return(
            lambda_proxy_response(status_code=200, headers_dict={}, 
            response_body=ratings_query_response)
            
        )
    else:
        logging.info("main - error_message " + str(error_message))
        return(
            lambda_proxy_response(status_code=404, headers_dict={}, 
            response_body=error_message)
            
        )

def lambda_handler(event, context):
    """Handles lambda invocation from cloudwatch events rule

        Parameters
        ----------

        Returns
        -------

        Raises
        ------
    """
    '''
        Logging required for cloudwatch logs
    '''
    logging.getLogger().setLevel(logging.INFO)

    logging.info("main - Lambda proxy event: ")
    logging.info(event)
    return(main(event=event))


if __name__ == "__main__":   
    main(event={"pathParameters":{"night":"2020-06-20"}})
