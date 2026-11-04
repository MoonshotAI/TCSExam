"""Launch Harbor with the verified local host-support image assignment."""
import hashlib
import json
import os
from argparse import Namespace
from pathlib import Path

from .harbor_support import normalized_context
from .layout import load
from .setup import cache_path


def kernel_probe_reference():
    explicit = os.environ.get('TCSEXAM_HARBOR_KERNEL_PROBE_IMAGE')
    if explicit:
        return explicit
    context = os.environ.get('DOCKER_CONTEXT') or None
    host = json.dumps([context, os.environ.get('DOCKER_HOST', '') if not context else ''])
    key = hashlib.sha256(host.encode()).hexdigest()[:16]
    path = cache_path(Namespace(cache=None, docker_context=context)) / 'hosts' / (key + '.json')
    if not path.is_file():
        return None
    report = load(Path(path))
    for row in report.get('host_support', []):
        if row.get('support_kind') == 'harbor_kernel_probe':
            return row.get('local_image') or row.get('image')
    return None


def configure_harbor():
    from harbor.environments.docker.docker import DockerEnvironment
    context, _ = normalized_context(cache_path(Namespace(cache=None)))
    DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH = context
    reference = kernel_probe_reference()
    if reference:
        DockerEnvironment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE = reference


def main():
    configure_harbor()
    from harbor.cli.main import app
    return app()


if __name__ == '__main__':
    raise SystemExit(main())
