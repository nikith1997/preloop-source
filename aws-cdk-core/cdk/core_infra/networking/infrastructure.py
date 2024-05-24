import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_s3 as s3
from aws_cdk import Stack, Tags
from constructs import Construct


class VPCSetup(Construct):
    def __init__(self, scope: Construct, id_: str):
        super().__init__(scope, id_)

        self.vpc_name = "vpc-preloop"
        self.vpc_cidr = "192.168.0.0/16"

        vpc_construct_id = "vpc"
        # audit_bucket_construct_id = "audit-bucket"
        # audit_bucket_name = "vpc-audit-bucket"
        # self.audit_bucket = s3.Bucket.from_bucket_name(
        # self, audit_bucket_construct_id, audit_bucket_name
        # )

        self.vpc: ec2.Vpc = ec2.Vpc(
            self,
            vpc_construct_id,
            vpc_name=self.vpc_name,
            ip_addresses=ec2.IpAddresses.cidr(self.vpc_cidr),
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC, name="Public", cidr_mask=20
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="Compute",
                    cidr_mask=20,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="Data",
                    cidr_mask=20,
                ),
            ],
            nat_gateways=1,
        )
