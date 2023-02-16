import subprocess
import os
import stat
import time
import urllib.request
from pathlib import Path


class EmbeddedDB:
    weaviate_binary_path = "./weaviate-server-embedded"
    weaviate_binary_url = "https://github.com/samos123/weaviate/releases/download/v1.17.3/weaviate-server"
    weaviate_persistence_data_path = "./weaviate-data"

    def ensure_weaviate_binary_exists(self):
        # TODO implement binary verification
        file = Path(self.weaviate_binary_path)
        if not file.exists():
            print(f"Binary {self.weaviate_binary_path} did not exist. "
                  f"Downloading binary from {self.weaviate_binary_url}")
            urllib.request.urlretrieve(self.weaviate_binary_url, self.weaviate_binary_path)
        # Ensuring weaviate binary is executable
        file.chmod(file.stat().st_mode | stat.S_IEXEC)

    def is_running(self) -> bool:
        binary_name = os.path.basename(self.weaviate_binary_path)
        result = subprocess.run(f'ps aux | grep {binary_name} | grep -v grep', shell=True, capture_output=True)
        if result.returncode == 1:
            return False
        else:
            output = result.stdout.decode("ascii")
            if binary_name in output:
                return True
        return False

    def start(self):
        if self.is_running():
            print("weaviate is already running")
            return

        self.ensure_weaviate_binary_exists()
        my_env = os.environ.copy()
        my_env.setdefault("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
        my_env.setdefault("PERSISTENCE_DATA_PATH", self.weaviate_persistence_data_path)
        subprocess.Popen(
            ["./weaviate-server-embedded", "--host", "127.0.0.1", "--port", "8080", "--scheme", "http"],
            env=my_env
        )


def ensure_embedded_db_running():
    embedded_db = EmbeddedDB()
    if not embedded_db.is_running():
        print("Embedded weaviate wasn't running, so starting embedded weaviate again")
        embedded_db.start()
        # TODO remove the sleep and check every 0.1 seconds if it's ready
        time.sleep(1)
