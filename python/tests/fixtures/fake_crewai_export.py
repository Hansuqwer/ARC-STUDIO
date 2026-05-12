import asyncio


class FakeAgent:
    role = "researcher"


class FakeTaskOutput:
    task_id = "research-task"
    agent = FakeAgent()
    raw = "task raw output"

    def __str__(self) -> str:
        return self.raw


class FakeCrewOutput:
    raw = "crew raw output"
    json_dict = {"ok": True}
    token_usage = {"total_tokens": 0}
    tasks_output = [FakeTaskOutput()]


class FakeCrew:
    def kickoff(self, inputs=None):
        return FakeCrewOutput()


class SlowCrew:
    async def akickoff(self, inputs=None):
        await asyncio.sleep(1)
        return FakeCrewOutput()


class CancelledCrew:
    async def akickoff(self, inputs=None):
        raise asyncio.CancelledError()


def make_crew(inputs=None):
    return FakeCrew()


def make_slow_crew(inputs=None):
    return SlowCrew()


def make_cancelled_crew(inputs=None):
    return CancelledCrew()
