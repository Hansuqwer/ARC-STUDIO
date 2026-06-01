import asyncio
import json

import pytest

from agent_runtime_cockpit.swarmgraph import (
    DurableNotificationOutbox,
    DurableWebhookNotificationHook,
    ManagedNotificationService,
    NotificationConfig,
    NotificationDeliveryRecord,
    NotificationServiceConfig,
    PushNotificationHook,
    SwarmGraphEvent,
    SwarmGraphEventBroadcaster,
    SwarmGraphEventKind,
    WebhookTargetConfig,
)


def _event() -> SwarmGraphEvent:
    return SwarmGraphEvent(kind=SwarmGraphEventKind.audit, swarm_id="swarm-test")


@pytest.mark.asyncio
async def test_managed_notification_service_start_stop_idempotent(tmp_path):
    hook = DurableWebhookNotificationHook(
        NotificationConfig(outbox_path=str(tmp_path / "outbox.jsonl"))
    )
    service = ManagedNotificationService(
        hook, NotificationServiceConfig(interval_seconds=60, max_batch=1)
    )

    first = await service.start()
    second = await service.start()
    stopped = await service.stop()
    stopped_again = await service.stop()

    assert first.state == "running"
    assert second.state == "running"
    assert stopped.state == "stopped"
    assert stopped_again.state == "stopped"


@pytest.mark.asyncio
async def test_managed_notification_service_flushes_outbox(tmp_path, monkeypatch):
    calls: list[str] = []

    def fake_post(self, target, payload):
        calls.append(payload["kind"])
        return True

    monkeypatch.setattr(DurableWebhookNotificationHook, "_post_sync", fake_post)
    outbox_path = tmp_path / "outbox.jsonl"
    hook = DurableWebhookNotificationHook(
        NotificationConfig(
            outbox_path=str(outbox_path),
            targets=[WebhookTargetConfig(id="wh-all", url="https://example.test/hook")],
        )
    )
    hook.outbox.append(
        NotificationDeliveryRecord(
            id="delivery-1",
            target_id="wh-all",
            event_kind="audit",
            event=_event().to_dict(),
            status="failed",
            attempt=1,
        )
    )

    result = await ManagedNotificationService(hook).flush_once()

    assert result.processed == 1
    assert result.delivered == 1
    assert calls == ["audit"]
    assert DurableNotificationOutbox(outbox_path).read()[-1].status == "delivered"


@pytest.mark.asyncio
async def test_managed_notification_service_abandons_after_max_attempts(tmp_path):
    outbox_path = tmp_path / "outbox.jsonl"
    hook = DurableWebhookNotificationHook(
        NotificationConfig(
            outbox_path=str(outbox_path),
            targets=[
                WebhookTargetConfig(id="wh-all", url="https://example.test/hook", max_attempts=1)
            ],
        )
    )
    hook.outbox.append(
        NotificationDeliveryRecord(
            id="delivery-1",
            target_id="wh-all",
            event_kind="audit",
            event=_event().to_dict(),
            status="failed",
            attempt=1,
        )
    )

    result = await ManagedNotificationService(hook).flush_once()

    assert result.abandoned == 1
    assert DurableNotificationOutbox(outbox_path).read()[-1].status == "abandoned"


@pytest.mark.asyncio
async def test_push_broadcaster_delivers_to_multiple_subscribers():
    broadcaster = SwarmGraphEventBroadcaster(queue_size=2)
    q1 = broadcaster.subscribe("swarm-test")
    q2 = broadcaster.subscribe("swarm-test")

    await PushNotificationHook(broadcaster).notify(_event())

    assert (await q1.get())["kind"] == "audit"
    assert (await q2.get())["kind"] == "audit"


@pytest.mark.asyncio
async def test_push_broadcaster_close_and_stream_cleanup():
    broadcaster = SwarmGraphEventBroadcaster(queue_size=2)
    seen: list[dict[str, object]] = []

    async def consume():
        async for item in broadcaster.stream("swarm-test"):
            seen.append(item)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    await broadcaster.publish(_event())
    await broadcaster.close("swarm-test")
    await task

    assert seen[0]["kind"] == "audit"


@pytest.mark.asyncio
async def test_push_broadcaster_drops_oldest_on_overflow():
    broadcaster = SwarmGraphEventBroadcaster(queue_size=1)
    queue = broadcaster.subscribe("swarm-test")
    first = _event()
    second = SwarmGraphEvent(
        kind=SwarmGraphEventKind.worker,
        swarm_id="swarm-test",
        data={"n": 2},
    )

    await broadcaster.publish(first)
    await broadcaster.publish(second)

    assert (await queue.get())["kind"] == "worker"


def test_notification_service_json_models_stable(tmp_path):
    status = ManagedNotificationService(
        DurableWebhookNotificationHook(
            NotificationConfig(outbox_path=str(tmp_path / "outbox.jsonl"))
        )
    ).status()

    payload = json.loads(status.model_dump_json())

    assert payload["state"] == "idle"
    assert payload["enabled"] is True
