# SPDX-License-Identifier: Apache-2.0
"""Small Docker Engine API client, requiring no registry credentials or SDK."""
import http.client
import json
import re
import socket
import urllib.parse

class DockerError(RuntimeError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f'Docker HTTP {status}: {message}')

class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path, timeout=60):
        super().__init__('localhost', timeout=timeout)
        self.path = path
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)

class Docker:
    def __init__(self, socket_path='/var/run/docker.sock'):
        self.socket_path = socket_path
        self.api_version = None

    def call(self, method, path, payload=None, *, raw=False, timeout=60):
        version = self.api_version or '1.41'
        try:
            return self._call(method, path, payload, raw=raw, timeout=timeout,
                              api_version=version)
        except DockerError as exc:
            if self.api_version is not None or exc.status != 400:
                raise
            match = re.search(r'Minimum supported API version is (\d+\.\d+)', exc.message)
            if match is None:
                raise
            self.api_version = match.group(1)
            return self._call(method, path, payload, raw=raw, timeout=timeout,
                              api_version=self.api_version)

    def _call(self, method, path, payload, *, raw, timeout, api_version):
        headers = {}
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode()
            headers['Content-Type'] = 'application/json'
        elif payload is not None:
            headers['Content-Type'] = 'application/x-tar'
        conn = UnixHTTP(self.socket_path, timeout)
        try:
            interrupted = None
            try:
                conn.request(method, '/v' + api_version + path, body=payload, headers=headers)
            except BrokenPipeError as exc:
                # Docker may reject an archive before consuming its body. Keep
                # the actual HTTP error when the daemon has already sent one.
                interrupted = exc
                if conn.sock is not None:
                    conn.sock.settimeout(min(timeout, 5))
            try:
                r = conn.getresponse()
                data = r.read()
            except (OSError, http.client.HTTPException) as exc:
                if interrupted is not None:
                    raise interrupted from exc
                raise
            if r.status >= 400:
                raise DockerError(r.status, data.decode(errors='replace')[:2000]) from interrupted
            if interrupted is not None:
                # A successful response cannot prove a truncated upload arrived.
                raise interrupted
            if raw:
                return data
            return json.loads(data) if data else None
        finally:
            conn.close()
    def inspect(self, container):
        return self.call('GET', f'/containers/{container}/json')
    def containers(self, all=True):
        return self.call('GET', '/containers/json?all=' + str(int(all)))
    def create(self, name, payload):
        return self.call('POST', '/containers/create?name=' + urllib.parse.quote(name), payload)['Id']
    def start(self, cid):
        return self.call('POST', f'/containers/{cid}/start')
    def remove(self, cid):
        try:
            return self.call('DELETE', f'/containers/{cid}?force=1&v=1')
        except DockerError as e:
            if e.status != 404:
                raise
    def put_archive(self, cid, dest, data):
        return self.call('PUT', f'/containers/{cid}/archive?path='+urllib.parse.quote(dest), data, raw=True, timeout=600)
    def archive(self, cid, path):
        return self.call('GET', f'/containers/{cid}/archive?path='+urllib.parse.quote(path), raw=True, timeout=600)
    def wait(self, cid, timeout):
        return self.call('POST', f'/containers/{cid}/wait', timeout=timeout)
