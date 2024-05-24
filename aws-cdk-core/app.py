#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.backend.components import BackEndAPI
from cdk.backend_certificates.components import BackendCertificates
from cdk.core_infra.components import CoreInfra
from cdk.emailer.components import Emailer
from cdk.execution_engine.components import CoreExecutionEngine
from cdk.frontend.components import FrontEnd
from cdk.model_endpoint.components import ModelEndpoint
from cdk.model_inference_engine.components import ModelInferenceEngine
from cdk.post_process_tasks.components import PostProcessTasks
from cdk.public_api.components import PreloopPublicApi
from cdk.waf.components import PreloopWaf

env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
)
deploy_env = os.getenv("CDK_DEPLOY_ENVIRONMENT")

app = cdk.App()
CoreInfra(app, "CoreInfra", env=env, deploy_env=deploy_env)
CoreExecutionEngine(app, "CoreExecutionEngine", env=env, deploy_env=deploy_env)
backend_api = BackEndAPI(app, "BackEndAPI", env=env, deploy_env=deploy_env)
backend_subdomain_certificate = None
public_domain_certificate = None
if deploy_env == "prod":
    backend_certificates = BackendCertificates(app, "BackendCertificates", env=env)
    backend_subdomain_certificate = backend_certificates.subdomain_certificate
    public_domain_certificate = backend_certificates.public_domain_certificate
    ModelEndpoint(app, "ModelEndpoint", env=env)

preloop_public_api = PreloopPublicApi(
    app,
    "PreloopPublicApi",
    alb_listener=backend_api.load_balancer_listener,
    preloop_api_certificate=backend_subdomain_certificate,
    env=env,
)
Emailer(app, "Emailer", env=env)
front_end = FrontEnd(
    app,
    "FrontEnd",
    env=env,
    deploy_env=deploy_env,
    certificate=public_domain_certificate,
)
PostProcessTasks(app, "PostProcessTasks", env=env, deploy_env=deploy_env)
ModelInferenceEngine(app, "ModelInferenceEngine", env=env)
if deploy_env == "prod":
    PreloopWaf(
        app, "PreloopWaf", front_end_alb=front_end.ecs_frontend.load_balancer, env=env
    )
app.synth()
