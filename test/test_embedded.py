from contextlib import ExitStack

import pytest

from weaviate import embedded


def test_cluster_ports_are_distinct_consecutive_pairs() -> None:
    gossip, data, raft, raft_rpc = embedded._get_cluster_ports()

    assert data == gossip + 1
    assert raft_rpc == raft + 1
    assert len({gossip, data, raft, raft_rpc}) == 4


def test_cluster_ports_skip_gossip_port_when_next_port_is_taken(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_hold_port = embedded._hold_port
    calls: list = []

    def hold_port_with_first_data_port_taken(held: ExitStack, port: int = 0) -> int:
        calls.append(port)
        if len(calls) == 2:
            raise OSError("address already in use")
        return real_hold_port(held, port)

    monkeypatch.setattr(embedded, "_hold_port", hold_port_with_first_data_port_taken)

    gossip, data, _, _ = embedded._get_cluster_ports()

    rejected_gossip = calls[1] - 1
    assert gossip != rejected_gossip
    assert data == gossip + 1
