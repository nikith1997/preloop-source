from aws_cdk import Stack
from constructs import Construct

from cdk.model_inference_engine.ecs.infrastructure import ModelInferenceEngineECS


class ModelInferenceEngine(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ModelInferenceEngineECS(self, "ModelInferenceEngineECS")
