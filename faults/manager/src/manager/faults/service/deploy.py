from dataclasses import dataclass
from kubernetes.client import V1Scale, V1ScaleSpec

import logging

logger = logging.getLogger(__name__)

@dataclass
class DeletePodsParameters:
    namespace: str
    name: str
    original_replicas: int



class DeletePods:


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.spec = spec

        # prepare output
        self.deployments = []

    def prepare(self):
        res = self.kubernetes_client.list_namespaced_deployment(
            namespace=self.spec["namespace"],
            label_selector=self.spec["label_selector"],
        )
        for deploy in res.items:
            self.deployments.append(DeletePodsParameters(namespace=deploy.metadata.namespace, name=deploy.metadata.name, original_replicas=deploy.spec.replicas))

    def execute(self):
        for deploy in self.deployments:
            logger.debug(f"DeletePods {deploy}")
            scale = V1Scale(spec={"replicas": 0})
            res = self.kubernetes_client.patch_namespaced_deployment_scale(
                deploy.name,
                deploy.namespace,
                scale 
            )
            logger.info(f"remove all deployment pods: namespace={deploy.namespace} name={deploy.name} original_replicas={deploy.original_replicas}")

    def recover(self):
        for deploy in self.deployments:
            scale = V1Scale(spec={"replicas": deploy.original_replicas})
            res = self.kubernetes_client.patch_namespaced_deployment_scale(
                deploy.name,
                deploy.namespace,
                scale 
            )
            logger.info(f"restore deployment to {deploy.original_replicas} replicas: namespace={deploy.namespace} name={deploy.name}")
