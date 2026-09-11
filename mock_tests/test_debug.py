import weaviate
from weaviate.classes.debug import DistributedTask
from pytest_httpserver import HTTPServer


def test_list_tasks(weaviate_client: weaviate.WeaviateClient, weaviate_mock: HTTPServer) -> None:
    weaviate_mock.expect_request("/v1/tasks").respond_with_json(
        {
            "reindex": [
                {
                    "id": "task-1",
                    "version": 1,
                    "status": "running",
                    "startedAt": "2026-01-01T00:00:00Z",
                    "finishedNodes": ["node1"],
                    "payload": {"collection": "MyCollection"},
                },
                {
                    "id": "task-2",
                    "version": 1,
                    "status": "finished",
                    "startedAt": "2026-01-01T00:00:00Z",
                    "finishedAt": "2026-01-01T00:05:00Z",
                    "finishedNodes": ["node1", "node2"],
                },
            ]
        }
    )

    tasks = weaviate_client.debug.list_tasks()

    assert list(tasks.keys()) == ["reindex"]
    assert len(tasks["reindex"]) == 2

    first = tasks["reindex"][0]
    assert isinstance(first, DistributedTask)
    assert first.id == "task-1"
    assert first.status == "running"
    assert first.finished_at is None
    assert first.finished_nodes == ["node1"]
    assert first.payload == {"collection": "MyCollection"}

    second = tasks["reindex"][1]
    assert second.id == "task-2"
    assert second.status == "finished"
    assert second.finished_nodes == ["node1", "node2"]


def test_list_tasks_empty(
    weaviate_client: weaviate.WeaviateClient, weaviate_mock: HTTPServer
) -> None:
    weaviate_mock.expect_request("/v1/tasks").respond_with_json({})

    tasks = weaviate_client.debug.list_tasks()

    assert tasks == {}
