from typing import List

from flask import Flask, g

from journey_tests.journeys import SyncJourneys

app = Flask(__name__)


def get_sync_client() -> SyncJourneys:
    if "sync" not in g:
        g.sync = SyncJourneys.use()
    return g.sync


@app.route("/sync-in-sync")
def sync() -> List[dict]:
    return get_sync_client().simple()


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
