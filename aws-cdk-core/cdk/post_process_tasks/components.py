from aws_cdk import Stack
from constructs import Construct

from cdk.post_process_tasks.www_redirect.infrastructure import FrontEndWWWRedirect


class PostProcessTasks(Stack):
    def __init__(self, scope: Construct, id_: str, deploy_env: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)

        if deploy_env == "prod":
            frontend_www_redirect = FrontEndWWWRedirect(
                self, "FrontEndWWWRedirect", deploy_env
            )
