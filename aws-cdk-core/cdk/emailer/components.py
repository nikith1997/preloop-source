from aws_cdk import Stack
from constructs import Construct

from cdk.emailer.lambda_function.infrastructure import EmailerLambda


class Emailer(Stack):
    def __init__(self, scope: Construct, id_: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)
        emailer_lambda = EmailerLambda(self, "EmailerLambda")
