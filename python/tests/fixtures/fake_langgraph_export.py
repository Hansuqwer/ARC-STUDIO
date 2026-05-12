class FakeCompiledGraph:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def invoke(self, inputs):
        if self.fail:
            raise RuntimeError("invoke failed with token=sk-test-redacted")
        return {"messages": ["ok"], "inputs": inputs}


class FakeStateGraph:
    def compile(self):
        return FakeCompiledGraph()


def make_graph():
    return FakeStateGraph()


async def make_graph_async():
    return FakeStateGraph()


def make_compiled_graph():
    return FakeCompiledGraph()


def make_failing_graph():
    return FakeCompiledGraph(fail=True)


def not_a_graph():
    return object()
