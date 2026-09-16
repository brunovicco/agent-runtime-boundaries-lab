import pytest

from agent_runtime_boundaries.adapters.memory_ledger import InMemoryEffectLedger


@pytest.mark.asyncio
async def test_ledger_returns_none_for_missing_key() -> None:
    ledger = InMemoryEffectLedger()
    assert await ledger.get_completed("missing") is None


@pytest.mark.asyncio
async def test_ledger_is_idempotent_for_same_payload() -> None:
    ledger = InMemoryEffectLedger()
    await ledger.complete("key-1", {"value": 1})
    await ledger.complete("key-1", {"value": 1})
    assert await ledger.get_completed("key-1") == {"value": 1}


@pytest.mark.asyncio
async def test_ledger_returns_a_copy() -> None:
    ledger = InMemoryEffectLedger()
    await ledger.complete("key-1", {"nested": {"value": 1}})
    loaded = await ledger.get_completed("key-1")
    assert loaded is not None
    loaded["nested"]["value"] = 2
    assert await ledger.get_completed("key-1") == {"nested": {"value": 1}}


@pytest.mark.asyncio
async def test_ledger_rejects_conflicting_payload() -> None:
    ledger = InMemoryEffectLedger()
    await ledger.complete("key-1", {"value": 1})
    with pytest.raises(RuntimeError):
        await ledger.complete("key-1", {"value": 2})
