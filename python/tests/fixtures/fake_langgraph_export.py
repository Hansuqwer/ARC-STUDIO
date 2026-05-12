class FakeCompiledGraph:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def invoke(self, inputs):
        if self.fail:
            raise RuntimeError("invoke failed with token=sk-test-redacted")
        return {"messages": ["ok"], "inputs": inputs}


class FakeStreamingGraph:
    def stream(self, inputs, stream_mode=None):
        yield ("messages", (FakeMessageChunk("hello "), {"langgraph_node": "agent"}))
        yield ("messages", (FakeMessageChunk("world"), {"langgraph_node": "agent"}))
        yield ("updates", {"agent": {"messages": ["hello world"], "inputs": inputs}})

    def invoke(self, inputs):
        return {"messages": ["fallback"], "inputs": inputs}


class FakeMessageChunk:
    def __init__(self, content: str) -> None:
        self.content = content


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


def make_streaming_graph():
    return FakeStreamingGraph()


def not_a_graph():
    return object()
