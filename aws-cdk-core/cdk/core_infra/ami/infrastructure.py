from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_imagebuilder as imagebuilder
from constructs import Construct

from cdk.core_infra.networking import infrastructure as network_infra


class GithubAMI(Construct):
    """
    AMI image for Github Actions.
    """

    def __init__(self, scope: Construct, id_: str):
        super().__init__(scope, id_)

        security_group_runner = ec2.SecurityGroup(
            self,
            "GithubActionsRunnerSG",
            vpc=network_infra.VPCSetup.vpc,
            security_group_name="github-actions-runner-sg",
            description="Github Actions Runner security group",
            allow_all_outbound=True,
        )

        self.ami = ec2.MachineImage(
            self,
            "GithubActionsAMI",
            name="github-actions-runner",
            description="Github Actions Runner",
            vpc=network_infra.VPCSetup.vpc,
            security_group=security_group_runner,
            instance_type=ec2.InstanceType("t3.xlarge"),
        )
        ec2.c
