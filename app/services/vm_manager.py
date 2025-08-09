from __future__ import annotations

import os
from typing import Dict

try:
    import docker  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    docker = None

from ..config import get_settings


settings = get_settings()


class VMManager:
    def __init__(self):
        # connect via docker socket if available, else fallback
        self.client = None
        if docker is not None:
            try:
                self.client = docker.from_env()
            except Exception:
                self.client = None
        self.image = os.environ.get(
            "VM_BASE_IMAGE",
            "ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest",
        )

    def create_vm(self, name_prefix: str = "vm-session") -> Dict:
        """Start a new VM container and return connection info.

        Returns: {container_id, novnc_port, vnc_port}
        """
        if self.client is None:
            # Fallback: use current API container's published ports
            # Note: compose maps 6080:6080 and 5901:5900
            return {"container_id": None, "novnc_port": 6080, "vnc_port": 5901}
        try:
            container = self.client.containers.run(
                self.image,
                name=f"{name_prefix}-{os.urandom(4).hex()}",
                detach=True,
                environment={
                    "WIDTH": str(os.environ.get("WIDTH", 1024)),
                    "HEIGHT": str(os.environ.get("HEIGHT", 768)),
                },
                ports={
                    "6080/tcp": None,  # random host port
                    "5900/tcp": None,
                },
                shm_size="2g",
            )
            container.reload()
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            novnc = ports.get("6080/tcp", [{}])[0].get("HostPort")
            vnc = ports.get("5900/tcp", [{}])[0].get("HostPort")
            return {
                "container_id": container.id,
                "novnc_port": int(novnc) if novnc else None,
                "vnc_port": int(vnc) if vnc else None,
            }
        except Exception:
            return {"container_id": None, "novnc_port": 6080, "vnc_port": 5901}

    def stop_vm(self, container_id: str) -> None:
        try:
            c = self.client.containers.get(container_id)
            c.stop(timeout=10)
            c.remove()
        except Exception:
            pass


vm_manager = VMManager()


