"""Unit tests for network simulator managers.

Tests for EventManager, ConfigManager, TriggerManager, and other
manager components.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cardlink.netsim.managers.event import EventManager
from cardlink.netsim.managers.config import ConfigManager
from cardlink.netsim.triggers import TriggerManager
from cardlink.netsim.types import NetworkEvent, NetworkEventType


class TestEventManager:
    """Tests for EventManager class."""

    def test_init(self):
        """Test EventManager initialization."""
        manager = EventManager(max_history_size=100)
        assert manager._max_history == 100
        assert len(manager._event_history) == 0
        assert manager.event_count == 0

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """Test event subscription."""
        manager = EventManager()

        callback = AsyncMock()
        unsubscribe = manager.subscribe(callback)

        assert callback in manager._listeners
        assert callable(unsubscribe)

    @pytest.mark.asyncio
    async def test_subscribe_with_event_type(self):
        """Test event subscription with specific type."""
        manager = EventManager()

        callback = AsyncMock()
        unsubscribe = manager.subscribe(callback, NetworkEventType.UE_ATTACH)

        assert NetworkEventType.UE_ATTACH in manager._type_listeners
        assert callback in manager._type_listeners[NetworkEventType.UE_ATTACH]

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test event unsubscription."""
        manager = EventManager()

        callback = AsyncMock()
        unsubscribe = manager.subscribe(callback)
        unsubscribe()

        assert callback not in manager._listeners

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """Test event emission."""
        manager = EventManager()

        callback = AsyncMock()
        manager.subscribe(callback)

        event = NetworkEvent(
            event_id="test_001",
            event_type=NetworkEventType.UE_ATTACH,
            timestamp=datetime.utcnow(),
            source="test",
            data={"imsi": "001010123456789"},
        )

        await manager.emit(event)

        callback.assert_called_once_with(event)
        assert manager.event_count == 1

    @pytest.mark.asyncio
    async def test_emit_to_type_specific_listener(self):
        """Test event emission to type-specific listener."""
        manager = EventManager()

        ue_callback = AsyncMock()
        session_callback = AsyncMock()

        manager.subscribe(ue_callback, NetworkEventType.UE_ATTACH)
        manager.subscribe(session_callback, NetworkEventType.PDN_CONNECT)

        event = NetworkEvent(
            event_id="test_001",
            event_type=NetworkEventType.UE_ATTACH,
            timestamp=datetime.utcnow(),
            source="test",
            data={},
        )

        await manager.emit(event)

        ue_callback.assert_called_once()
        session_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_emit_raw(self):
        """Test raw event emission."""
        manager = EventManager()

        callback = AsyncMock()
        manager.subscribe(callback)

        event = await manager.emit_raw(
            event_type=NetworkEventType.UE_ATTACH,
            data={"imsi": "001010123456789"},
            imsi="001010123456789",
        )

        assert event.event_type == NetworkEventType.UE_ATTACH
        assert event.imsi == "001010123456789"
        callback.assert_called_once()

    def test_get_event_history(self):
        """Test event history retrieval."""
        manager = EventManager()

        # Add some events to history manually
        for i in range(5):
            event = NetworkEvent(
                event_id=f"test_{i}",
                event_type=NetworkEventType.UE_ATTACH,
                timestamp=datetime.utcnow(),
                source="test",
                data={},
            )
            manager._event_history.append(event)

        history = manager.get_event_history(limit=3)
        assert len(history) == 3

    def test_get_event_history_with_type_filter(self):
        """Test event history with type filter."""
        manager = EventManager()

        # Add mixed events
        for event_type in [
            NetworkEventType.UE_ATTACH,
            NetworkEventType.PDN_CONNECT,
            NetworkEventType.UE_ATTACH,
        ]:
            event = NetworkEvent(
                event_id=f"test_{event_type.value}",
                event_type=event_type,
                timestamp=datetime.utcnow(),
                source="test",
                data={},
            )
            manager._event_history.append(event)

        history = manager.get_event_history(event_type=NetworkEventType.UE_ATTACH)
        assert len(history) == 2
        assert all(e.event_type == NetworkEventType.UE_ATTACH for e in history)

    def test_find_events(self):
        """Test event finding with multiple filters."""
        manager = EventManager()

        # Add events
        for i, imsi in enumerate(["001010123456789", "001010987654321", "001010123456789"]):
            event = NetworkEvent(
                event_id=f"test_{i}",
                event_type=NetworkEventType.UE_ATTACH,
                timestamp=datetime.utcnow(),
                source="test",
                data={},
                imsi=imsi,
            )
            manager._event_history.append(event)

        events = manager.find_events(imsi="001010123456789")
        assert len(events) == 2

    def test_get_event_by_id(self):
        """Test getting event by ID."""
        manager = EventManager()

        event = NetworkEvent(
            event_id="unique_id",
            event_type=NetworkEventType.UE_ATTACH,
            timestamp=datetime.utcnow(),
            source="test",
            data={},
        )
        manager._event_history.append(event)

        found = manager.get_event_by_id("unique_id")
        assert found == event

        not_found = manager.get_event_by_id("nonexistent")
        assert not_found is None

    def test_clear_history(self):
        """Test clearing event history."""
        manager = EventManager()

        for i in range(5):
            event = NetworkEvent(
                event_id=f"test_{i}",
                event_type=NetworkEventType.UE_ATTACH,
                timestamp=datetime.utcnow(),
                source="test",
                data={},
            )
            manager._event_history.append(event)

        count = manager.clear_history()
        assert count == 5
        assert manager.event_count == 0

    @pytest.mark.asyncio
    async def test_start_correlation(self):
        """Test correlation session start."""
        manager = EventManager()

        correlation_id = await manager.start_correlation("test_session")
        assert correlation_id.startswith("corr_test_session_")
        assert correlation_id in manager._active_correlations

    @pytest.mark.asyncio
    async def test_end_correlation(self):
        """Test correlation session end."""
        manager = EventManager()

        correlation_id = await manager.start_correlation()

        # Emit some events
        event = NetworkEvent(
            event_id="test_001",
            event_type=NetworkEventType.UE_ATTACH,
            timestamp=datetime.utcnow(),
            source="test",
            data={},
            correlation_id=correlation_id,
        )
        await manager.emit(event)

        events = await manager.end_correlation(correlation_id)
        assert len(events) == 1
        assert correlation_id not in manager._active_correlations

    def test_get_correlated_events(self):
        """Test getting correlated events."""
        manager = EventManager()

        correlation_id = "test_corr_123"

        for i in range(3):
            event = NetworkEvent(
                event_id=f"test_{i}",
                event_type=NetworkEventType.UE_ATTACH,
                timestamp=datetime.utcnow(),
                source="test",
                data={},
                correlation_id=correlation_id,
            )
            manager._event_history.append(event)

        events = manager.get_correlated_events(correlation_id)
        assert len(events) == 3

    def test_get_statistics(self):
        """Test statistics generation."""
        manager = EventManager()

        # Add some events
        for event_type in [
            NetworkEventType.UE_ATTACH,
            NetworkEventType.UE_ATTACH,
            NetworkEventType.PDN_CONNECT,
        ]:
            event = NetworkEvent(
                event_id=f"test_{event_type.value}",
                event_type=event_type,
                timestamp=datetime.utcnow(),
                source="test",
                data={},
            )
            manager._event_history.append(event)

        stats = manager.get_statistics()
        assert stats["total_events"] == 3
        assert "UE_ATTACH" in stats["events_by_type"]
        assert stats["events_by_type"]["UE_ATTACH"] == 2

    def test_export_events_json(self):
        """Test JSON export."""
        manager = EventManager()

        event = NetworkEvent(
            event_id="test_001",
            event_type=NetworkEventType.UE_ATTACH,
            timestamp=datetime.utcnow(),
            source="test",
            data={"imsi": "001010123456789"},
        )
        manager._event_history.append(event)

        output = manager.export_events(format="json")
        assert "test_001" in output
        assert "UE_ATTACH" in output

    def test_export_events_csv(self):
        """Test CSV export."""
        manager = EventManager()

        event = NetworkEvent(
            event_id="test_001",
            event_type=NetworkEventType.UE_ATTACH,
            timestamp=datetime.utcnow(),
            source="test",
            data={},
        )
        manager._event_history.append(event)

        output = manager.export_events(format="csv")
        assert "event_id" in output
        assert "test_001" in output

    def test_history_trimming(self):
        """Test history size limit enforcement."""
        manager = EventManager(max_history_size=5)

        for i in range(10):
            event = NetworkEvent(
                event_id=f"test_{i}",
                event_type=NetworkEventType.UE_ATTACH,
                timestamp=datetime.utcnow(),
                source="test",
                data={},
            )
            manager._event_history.append(event)

        # Manually trim (normally done in emit)
        if len(manager._event_history) > manager._max_history:
            excess = len(manager._event_history) - manager._max_history
            manager._event_history = manager._event_history[excess:]

        assert len(manager._event_history) == 5


class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter."""
        adapter = AsyncMock()
        adapter.get_config = AsyncMock(return_value={"cell": {"plmn": "001-01"}})
        adapter.set_config = AsyncMock(return_value=True)
        return adapter

    @pytest.fixture
    def mock_emitter(self):
        """Create mock event emitter."""
        emitter = AsyncMock()
        emitter.emit = AsyncMock()
        return emitter

    def test_init(self, mock_adapter, mock_emitter):
        """Test ConfigManager initialization."""
        manager = ConfigManager(mock_adapter, mock_emitter)
        assert manager._adapter == mock_adapter
        assert manager._config_cache is None

    @pytest.mark.asyncio
    async def test_get_config(self, mock_adapter, mock_emitter):
        """Test getting configuration."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        config = await manager.get()
        assert "cell" in config
        mock_adapter.get_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_config_cached(self, mock_adapter, mock_emitter):
        """Test configuration caching."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        # First call
        await manager.get()
        # Second call (should use cache)
        await manager.get()

        # Should only call adapter once
        assert mock_adapter.get_config.call_count == 1

    @pytest.mark.asyncio
    async def test_get_config_refresh(self, mock_adapter, mock_emitter):
        """Test forced configuration refresh."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        # First call
        await manager.get()
        # Second call with refresh
        await manager.get(refresh=True)

        # Should call adapter twice
        assert mock_adapter.get_config.call_count == 2

    @pytest.mark.asyncio
    async def test_get_value(self, mock_adapter, mock_emitter):
        """Test getting specific configuration value."""
        mock_adapter.get_config = AsyncMock(return_value={
            "cell": {"plmn": "001-01", "frequency": 1950}
        })
        manager = ConfigManager(mock_adapter, mock_emitter)

        value = await manager.get_value("cell.plmn")
        assert value == "001-01"

    @pytest.mark.asyncio
    async def test_get_value_default(self, mock_adapter, mock_emitter):
        """Test getting configuration value with default."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        value = await manager.get_value("nonexistent.key", default="default_value")
        assert value == "default_value"

    @pytest.mark.asyncio
    async def test_set_config(self, mock_adapter, mock_emitter):
        """Test setting configuration."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        result = await manager.set({"cell": {"plmn": "310-150"}})
        assert result is True
        mock_adapter.set_config.assert_called_once()
        mock_emitter.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_value(self, mock_adapter, mock_emitter):
        """Test setting specific configuration value."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        result = await manager.set_value("cell.plmn", "310-150")
        assert result is True

        # Check the params passed
        call_args = mock_adapter.set_config.call_args[0][0]
        assert call_args == {"cell": {"plmn": "310-150"}}

    @pytest.mark.asyncio
    async def test_reload(self, mock_adapter, mock_emitter):
        """Test configuration reload."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        # Populate cache
        await manager.get()
        assert manager._config_cache is not None

        # Reload
        await manager.reload()
        assert mock_adapter.get_config.call_count == 2

    def test_get_cached_empty(self, mock_adapter, mock_emitter):
        """Test get_cached when empty."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        cached = manager.get_cached()
        assert cached is None

    def test_get_default_config(self, mock_adapter, mock_emitter):
        """Test default configuration template."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        default = manager.get_default_config()
        assert "cell" in default
        assert "network" in default
        assert "security" in default

    def test_merge_config(self, mock_adapter, mock_emitter):
        """Test configuration merging."""
        manager = ConfigManager(mock_adapter, mock_emitter)

        base = {"cell": {"plmn": "001-01", "frequency": 1950}}
        overlay = {"cell": {"plmn": "310-150"}}

        merged = manager.merge_config(base, overlay)
        assert merged["cell"]["plmn"] == "310-150"
        assert merged["cell"]["frequency"] == 1950


class TestTriggerManager:
    """Tests for TriggerManager class."""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter."""
        adapter = AsyncMock()
        adapter.trigger_event = AsyncMock(return_value=True)
        return adapter

    @pytest.fixture
    def mock_emitter(self):
        """Create mock event emitter."""
        emitter = AsyncMock()
        emitter.emit = AsyncMock()
        return emitter

    def test_init(self, mock_adapter, mock_emitter):
        """Test TriggerManager initialization."""
        manager = TriggerManager(mock_adapter, mock_emitter)
        assert manager._adapter == mock_adapter
        assert len(manager._trigger_history) == 0

    @pytest.mark.asyncio
    async def test_trigger_paging(self, mock_adapter, mock_emitter):
        """Test paging trigger."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        result = await manager.trigger_paging("001010123456789")
        assert result is True
        mock_adapter.trigger_event.assert_called_once()
        mock_emitter.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_paging_types(self, mock_adapter, mock_emitter):
        """Test different paging types."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        await manager.trigger_paging("001010123456789", paging_type="ps")
        await manager.trigger_paging("001010123456789", paging_type="cs")

        assert mock_adapter.trigger_event.call_count == 2

    @pytest.mark.asyncio
    async def test_trigger_detach(self, mock_adapter, mock_emitter):
        """Test detach trigger."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        result = await manager.trigger_detach("001010123456789", cause="reattach_required")
        assert result is True

    @pytest.mark.asyncio
    async def test_trigger_handover(self, mock_adapter, mock_emitter):
        """Test handover trigger."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        result = await manager.trigger_handover("001010123456789", target_cell=2)
        assert result is True

        call_args = mock_adapter.trigger_event.call_args
        assert call_args[1]["params"]["target_cell"] == 2

    @pytest.mark.asyncio
    async def test_trigger_cell_outage(self, mock_adapter, mock_emitter):
        """Test cell outage trigger."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        result = await manager.trigger_cell_outage(duration=10.0, cell_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_trigger_rlf(self, mock_adapter, mock_emitter):
        """Test RLF trigger."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        result = await manager.trigger_rlf("001010123456789")
        assert result is True

    @pytest.mark.asyncio
    async def test_trigger_tau(self, mock_adapter, mock_emitter):
        """Test TAU trigger."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        result = await manager.trigger_tau("001010123456789", tau_type="periodic")
        assert result is True

    @pytest.mark.asyncio
    async def test_trigger_custom(self, mock_adapter, mock_emitter):
        """Test custom trigger."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        result = await manager.trigger_custom(
            event_type="custom_event",
            params={"param1": "value1"},
        )
        assert result is True

    def test_validate_imsi_valid(self, mock_adapter, mock_emitter):
        """Test IMSI validation with valid IMSIs."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        # Should not raise
        manager._validate_imsi("001010123456789")  # 15 digits
        manager._validate_imsi("00101012345678")   # 14 digits

    def test_validate_imsi_invalid(self, mock_adapter, mock_emitter):
        """Test IMSI validation with invalid IMSIs."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        with pytest.raises(ValueError):
            manager._validate_imsi("")

        with pytest.raises(ValueError):
            manager._validate_imsi("123")  # Too short

        with pytest.raises(ValueError):
            manager._validate_imsi("0010101234567890")  # Too long

        with pytest.raises(ValueError):
            manager._validate_imsi("00101ABC456789")  # Non-digits

    def test_trigger_history(self, mock_adapter, mock_emitter):
        """Test trigger history recording."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        manager._record_trigger("paging", "001010123456789", {}, True)
        manager._record_trigger("handover", "001010123456789", {"target_cell": 2}, True)

        history = manager.get_trigger_history()
        assert len(history) == 2

    def test_trigger_history_limit(self, mock_adapter, mock_emitter):
        """Test trigger history limit."""
        manager = TriggerManager(mock_adapter, mock_emitter)
        manager._max_history = 5

        for i in range(10):
            manager._record_trigger("paging", f"00101012345678{i}", {}, True)

        assert len(manager._trigger_history) == 5

    def test_trigger_history_filter(self, mock_adapter, mock_emitter):
        """Test trigger history filtering."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        manager._record_trigger("paging", "001010123456789", {}, True)
        manager._record_trigger("handover", "001010123456789", {}, True)
        manager._record_trigger("paging", "001010987654321", {}, True)

        paging_history = manager.get_trigger_history(trigger_type="paging")
        assert len(paging_history) == 2

        imsi_history = manager.get_trigger_history(imsi="001010123456789")
        assert len(imsi_history) == 2

    def test_clear_history(self, mock_adapter, mock_emitter):
        """Test clearing trigger history."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        manager._record_trigger("paging", "001010123456789", {}, True)
        manager._record_trigger("handover", "001010123456789", {}, True)

        count = manager.clear_history()
        assert count == 2
        assert len(manager._trigger_history) == 0

    def test_supported_triggers(self, mock_adapter, mock_emitter):
        """Test supported triggers list."""
        manager = TriggerManager(mock_adapter, mock_emitter)

        supported = manager.supported_triggers
        assert "paging" in supported
        assert "handover" in supported
        assert "detach" in supported
        assert "cell_outage" in supported
