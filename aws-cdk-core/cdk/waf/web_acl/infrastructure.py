import aws_cdk.aws_wafv2 as wafv2
from aws_cdk.aws_apigatewayv2 import HttpApi
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationLoadBalancer
from constructs import Construct


class WebAcl(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        front_end_alb: ApplicationLoadBalancer,
    ) -> None:
        super().__init__(scope, id)

        web_acl = wafv2.CfnWebACL(
            self,
            "PreloopWebAcl",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            scope="REGIONAL",
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="PreloopWebAcl",
                sampled_requests_enabled=True,
            ),
            name="PreloopWebAcl",
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="CRSRule",
                    priority=1,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            name="AWSManagedRulesCommonRuleSet",
                            vendor_name="AWS",
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="CRSRule",
                        sampled_requests_enabled=True,
                    ),
                )
            ],
        )

        wafv2.CfnWebACLAssociation(
            self,
            "PreloopWebAclAssociation",
            resource_arn=front_end_alb.load_balancer_arn,
            web_acl_arn=web_acl.attr_arn,
        )
