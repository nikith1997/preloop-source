import os
from preloop.sdk import PreloopClient, RetrainMLModelRequest
import logging

log = logging.getLogger(__name__)

def lambda_handler(event, context):
    preloop_client = PreloopClient(endpoint_url=os.environ['PRELOOP_API_ENDPOINT'], 
                                   key_id=event['key_id'], 
                                   secret=event['secret'])

    response = preloop_client.retrain_ml_model(RetrainMLModelRequest(ml_model_id=event['ml_model_id']))

    return {
        'statusCode': 200,
        'body': response
    }
