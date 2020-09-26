import boto3
import json
import logging
import os

from boto3.dynamodb.conditions import Key

from microlib.microlib import get_boto_clients
from microlib.microlib import lambda_proxy_response


def clean_path_parameter_string(year):
    """Validates the year path parameter

        Parameters
        ----------
        year : str
            year passed to the request

        Returns
        -------
        valid_year : boolean
            

        Raises
        ------
    """
    if len(year) >= 5:
        logging.info("clean_path_parameter_string - string length")
        return(False)

    return(year.isnumeric())


def validate_request_parameters(event):
    """Validates the request passed in via the lambda handler event

        Parameters
        ----------
        event : dict
            lambda_handler event from api gateway

        Returns
        -------
        error_response : boolean
            

        Raises
        ------
    """
    error_response = None
    try:
        assert clean_path_parameter_string(event["pathParameters"]["year"]) is True, (
            "year parameter invalid"
        )
        logging.info("validate_request_parameters - year parameter valid")

    except KeyError:
        logging.info("validate_request_parameters - year parameter not found in request")
        error_response = {
            "message": "Path parameter year is required",
            "status_code": 400 
        }

    except AssertionError:
        logging.info("validate_request_parameters - year parameter invalid")
        error_response = {
            "message": "Invalid year path parameter, must be numeric",
            "status_code": 404 
        }

    return(error_response)

def dynamodb_show_request(show_name):
    """Query using the SHOW_ACCESS GSI

        Parameters
        ----------
        show_name : str
            Name of the show to request

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

    logging.info("dynamodb_show_request - DYNAMO_TABLE_NAME" + dynamo_table_name)
    dynamo_client, dynamo_table = get_boto_clients(
            resource_name="dynamodb",
            region_name="us-east-1",
            table_name=dynamo_table_name
    )

    logging.info("dynamodb_show_request - show_access_query" )

    '''
        Query one show using the GSI
    '''
    show_access_query = dynamo_table.query(
        IndexName="SHOW_ACCESS",
        KeyConditionExpression=Key("SHOW").eq(show_name)
    )

    show_ratings = show_access_query["Items"]
    logging.info("dynamodb_show_request - Count " + str(show_access_query["Count"]))

    '''
        If no items returned
    '''
    if show_access_query["Count"] == 0:
        error_message = {
            "message": "show: {show_name} not found".format(
                show_name=show_name
            )
        }
    else:
        logging.info("dynamodb_show_request - preparing year for serialization")
        '''
            convert from decimal to str for json serialization
        '''
        for individual_show in show_ratings:
            try:
                individual_show["YEAR"] = str(individual_show["YEAR"])
            except KeyError:
                logging.info("dynamodb_show_request - No year for " + individual_show["SHOW"])
        
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

    if error_response is not None:
        '''
            return http 400 level error response
        '''
        return(lambda_proxy_response(status_code=error_response["status_code"], 
        headers_dict={}, response_body=error_response.pop("status_code")))


    error_message, show_access_query = dynamodb_show_request(
        show_name=event["pathParameters"]["show"]
    )

    if error_message is None:
        logging.info("main - returning show_access_query" + str(len(show_access_query)))
        return(
            lambda_proxy_response(status_code=200, headers_dict={}, 
            response_body=show_access_query)
            
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
    main(event={"pathParameters":{"show":"Star Wars the Clone Wars"}})
