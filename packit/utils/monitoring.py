# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import logging
import os

logger = logging.getLogger(__name__)


class Pushgateway:
    def __init__(self) -> None:
        try:
            from prometheus_client import CollectorRegistry, Counter
        except ImportError:
            return
        else:
            self.pushgateway_address = os.getenv("PUSHGATEWAY_ADDRESS")
            self.worker_name = os.getenv("HOSTNAME")
            self.registry = CollectorRegistry()

            self.aliases_fallback_used = Counter(
                "aliases_fallback_used",
                "Number of times fallback values for aliases were used",
                registry=self.registry,
            )

    def push(self) -> None:
        try:
            from prometheus_client import push_to_gateway
        except ImportError:
            return
        else:
            if (
                not hasattr(self, "pushgateway_address")
                or not hasattr(self, "worker_name")
                or not hasattr(self, "registry")
            ):
                return
            if not (self.pushgateway_address and self.worker_name):
                logger.debug("Pushgateway address or worker name not defined.")
                return
            logger.info("Pushing the metrics to pushgateway.")
            push_to_gateway(
                self.pushgateway_address,
                job=self.worker_name,
                registry=self.registry,
            )
