from xdist.scheduler.loadscope import LoadScopeScheduling  # type: ignore


class MyScheduler(LoadScopeScheduling):
    def _split_scope(self, nodeid: str) -> str:
        # certain tests cannot run in parallel, so we need to make sure they are assigned to the same node
        if "mock_test/" in nodeid:
            return "mock_test"
        return nodeid


def pytest_xdist_make_scheduler(config: object, log: object) -> MyScheduler:
    return MyScheduler(config, log)
