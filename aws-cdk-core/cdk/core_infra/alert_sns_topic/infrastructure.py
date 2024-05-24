from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from constructs import Construct


class AlertSnsTopic(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        self.topic = sns.Topic(
            scope,
            "Topic",
            display_name="CoreInfraAlerts",
            topic_name="core-infra-alerts",
        )
        self.topic.add_subscription(
            subscriptions.EmailSubscription(
                email_address="preloop-engineering@preloop.com"
            )
        )
