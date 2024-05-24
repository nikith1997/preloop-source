from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class FrontEndWWWRedirect(Construct):
    def __init__(self, scope: Construct, id_: str, deploy_env: str):
        super().__init__(scope, id_)

        self.load_balancer_arn = ssm.StringParameter.value_from_lookup(
            self, parameter_name="/preloop/frontend/load-balancer-arn"
        )

        self.load_balancer_frontend = elbv2.ApplicationLoadBalancer.from_lookup(
            # lookup load balancer from ssm string parameter name "/preloop/frontend/load-balancer-arn"
            self,
            "PreloopFrontendLoadBalancer",
            load_balancer_arn=self.load_balancer_arn,
        )

        # get listener from load balancer, port 80. This already exists so
        # perform lookup
        self.listener_80 = elbv2.ApplicationListener.from_lookup(
            self,
            "PreloopFrontendListener80",
            listener_port=80,
            load_balancer_arn=self.load_balancer_arn,
        )

        # add redirect to listener. If host header is "preloop.com", redirect
        # to https://www.preloop.com. The code for CDK on the listener_80
        # is given below
        self.listener_80.add_action(
            "PreloopFrontendListener80Redirect",
            priority=1,
            conditions=[elbv2.ListenerCondition.host_headers(["preloop.com"])],
            action=elbv2.ListenerAction.redirect(
                port="443",
                protocol="HTTPS",
                host="www.preloop.com",
                path="/#{path}",
                query="#{query}",
                permanent=True,
            ),
        )

        self.listener_443 = elbv2.ApplicationListener.from_lookup(
            self,
            "PreloopFrontendListener443",
            listener_port=443,
            load_balancer_arn=self.load_balancer_arn,
        )

        self.listener_443.add_action(
            "PreloopFrontendListener443Redirect",
            priority=1,
            conditions=[elbv2.ListenerCondition.host_headers(["preloop.com"])],
            action=elbv2.ListenerAction.redirect(
                port="443",
                protocol="HTTPS",
                host="www.preloop.com",
                path="/#{path}",
                query="#{query}",
                permanent=True,
            ),
        )
