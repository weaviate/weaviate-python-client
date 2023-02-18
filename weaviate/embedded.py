import hashlib
import subprocess
import os
import signal
import stat
import time
from urllib.parse import urlparse, parse_qsl
import urllib.request
from pathlib import Path
import socket

from weaviate.exceptions import WeaviateStartUpError

weaviate_binary_path = "./weaviate-server-embedded"
weaviate_binary_url = (
    "https://github.com/samos123/weaviate/releases/download/v1.17.3/weaviate-server"
)
weaviate_persistence_data_path = "./weaviate-data"
weaviate_binary_md5 = "38b8ac3c77cc8707999569ae3fe34c71"


class EmbeddedDB:
    # TODO add a stop function that gets called when python process exits
    def __init__(self, url: str = ""):
        parsed = parse_qsl(urlparse(url).query)
        parsed = dict(parsed)
        self.port = int(parsed.get("port", 6666))
        self.pid = 0

    def __del__(self):
        self.stop()

    def ensure_weaviate_binary_exists(self):
        file = Path(weaviate_binary_path)
        if not file.exists():
            print(
                f"Binary {weaviate_binary_path} did not exist. "
                f"Downloading binary from {weaviate_binary_url}"
            )
            urllib.request.urlretrieve(weaviate_binary_url, weaviate_binary_path)
            # Ensuring weaviate binary is executable
            file.chmod(file.stat().st_mode | stat.S_IEXEC)
            with open(file, "rb") as f:
                assert (
                    hashlib.md5(f.read()).hexdigest() == weaviate_binary_md5
                ), f"md5 of binary {weaviate_binary_path} did not match {weaviate_binary_md5}"

    def is_running(self) -> bool:
        binary_name = os.path.basename(weaviate_binary_path)
        result = subprocess.run(
            f"ps aux | grep {binary_name} | grep -v grep", shell=True, capture_output=True
        )
        if result.returncode == 1:
            return False
        else:
            output = result.stdout.decode("ascii")
            if binary_name in output:
                return True
        return False

    def is_listening(self) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("127.0.0.1", self.port))
            s.close()
            return True
        except socket.error:
            s.close()
            return False

    def wait_till_listening(self):
        seconds = 30
        sleep_interval = 0.1
        retries = int(10 * (seconds / sleep_interval))
        while self.is_listening() is False and retries > 0:
            time.sleep(sleep_interval)
            retries -= 1
        if retries == 0:
            raise WeaviateStartUpError(
                f"Embedded DB did not start listening on port {self.port} within {seconds} seconds"
            )

    def start(self):
        if self.is_running():
            print("embedded weaviate is already running")
            return

        self.ensure_weaviate_binary_exists()
        my_env = os.environ.copy()
        my_env.setdefault("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
        my_env.setdefault("PERSISTENCE_DATA_PATH", weaviate_persistence_data_path)
        my_env.setdefault("CLUSTER_HOSTNAME", "embedded")
        my_env.setdefault(
            "ENABLE_MODULES",
            "text2vec-openai,text2vec-cohere,text2vec-huggingface,ref2vec-centroid,generative-openai,qna-openai",
        )
        process = subprocess.Popen(
            [
                f"{weaviate_binary_path}",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--scheme",
                "http",
            ],
            env=my_env,
        )
        self.pid = process.pid
        print(f"Started {weaviate_binary_path}: process ID {self.pid}")
        self.wait_till_listening()

    def stop(self):
        if self.pid > 0:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                print(
                    f"Tried to stop embedded weaviate process {self.pid}. Process {self.pid} "
                    f"was not found. So not doing anything"
                )

    def ensure_running(self):
        if not self.is_running():
            print("Embedded weaviate wasn't running, so starting embedded weaviate again")
            self.start()
