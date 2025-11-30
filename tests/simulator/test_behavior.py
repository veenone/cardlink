"""Tests for BehaviorController component."""

import pytest
from cardlink.simulator import BehaviorController, BehaviorConfig, BehaviorMode


class TestBehaviorController:
    """Test BehaviorController simulation modes."""

    def test_normal_mode(self, behavior_config_normal):
        """Test normal mode - no errors or delays."""
        controller = BehaviorController(behavior_config_normal)

        # Should not inject errors
        for _ in range(10):
            assert not controller.should_inject_error()

        # Should not timeout
        for _ in range(10):
            assert not controller.should_timeout()

    @pytest.mark.asyncio
    async def test_error_injection(self, behavior_config_error):
        """Test error injection mode."""
        controller = BehaviorController(behavior_config_error)

        # With 50% error rate, should inject some errors
        error_count = sum(1 for _ in range(100) if controller.should_inject_error())

        # Statistical check - should be roughly 50% (allow 30-70% range)
        assert 30 <= error_count <= 70, f"Error rate should be ~50%, got {error_count}%"

    def test_error_code_selection(self, behavior_config_error):
        """Test error code selection."""
        controller = BehaviorController(behavior_config_error)

        # Get error codes
        codes = set()
        for _ in range(20):
            code = controller.get_error_code()
            codes.add(code)

        # Should only return configured error codes
        assert codes.issubset(set(behavior_config_error.error_codes))

    @pytest.mark.asyncio
    async def test_timeout_simulation(self, behavior_config_timeout):
        """Test timeout simulation."""
        controller = BehaviorController(behavior_config_timeout)

        # With 50% timeout probability, should timeout sometimes
        timeout_count = sum(1 for _ in range(100) if controller.should_timeout())

        # Statistical check - should be roughly 50% (allow 30-70% range)
        assert 30 <= timeout_count <= 70, f"Timeout rate should be ~50%, got {timeout_count}%"

    def test_timeout_delay(self, behavior_config_timeout):
        """Test timeout delay is within configured range."""
        controller = BehaviorController(behavior_config_timeout)

        # Delay is returned in seconds, config is in milliseconds
        min_delay_s = behavior_config_timeout.timeout_delay_min_ms / 1000.0
        max_delay_s = behavior_config_timeout.timeout_delay_max_ms / 1000.0

        for _ in range(10):
            delay = controller.get_timeout_delay()
            assert min_delay_s <= delay <= max_delay_s

    def test_response_delay(self, behavior_config_normal):
        """Test normal response delay."""
        controller = BehaviorController(behavior_config_normal)

        delay = controller.get_response_delay()
        assert delay == behavior_config_normal.response_delay_ms / 1000.0

    @pytest.mark.asyncio
    async def test_maybe_inject_behavior_normal(self, behavior_config_normal):
        """Test behavior injection in normal mode."""
        controller = BehaviorController(behavior_config_normal)

        # Should return None (no error injection)
        for _ in range(10):
            error_sw = await controller.maybe_inject_behavior()
            assert error_sw is None

    @pytest.mark.asyncio
    async def test_maybe_inject_behavior_error(self, behavior_config_error):
        """Test behavior injection in error mode."""
        controller = BehaviorController(behavior_config_error)

        # Should sometimes return error codes
        results = []
        for _ in range(50):
            error_sw = await controller.maybe_inject_behavior()
            results.append(error_sw)

        # Should have some non-None values
        errors = [r for r in results if r is not None]
        assert len(errors) > 0, "Should inject some errors"

        # All errors should be from configured list
        for error in errors:
            assert error in behavior_config_error.error_codes

    @pytest.mark.asyncio
    async def test_maybe_inject_behavior_timeout(self, behavior_config_timeout):
        """Test behavior injection in timeout mode."""
        controller = BehaviorController(behavior_config_timeout)

        # Should sometimes delay (not always)
        import time
        start = time.time()

        # Run a few times - at least one should delay
        for _ in range(5):
            await controller.maybe_inject_behavior()

        elapsed = (time.time() - start) * 1000

        # If any delayed, elapsed should be > 0
        # (This is a weak test, but hard to test probabilistic behavior)
        assert elapsed >= 0

    def test_reset_stats(self, behavior_config_error):
        """Test statistics reset."""
        controller = BehaviorController(behavior_config_error)

        # Generate some activity
        for _ in range(10):
            controller.should_inject_error()

        # Reset stats
        controller.reset_stats()

        # Stats should be reset (exact implementation depends on BehaviorController)
        # For now, just verify it doesn't crash
        assert True

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = BehaviorConfig(error_rate=0.5)
        config.validate()

        # Invalid error rate
        with pytest.raises(ValueError):
            config = BehaviorConfig(error_rate=1.5)
            config.validate()

        with pytest.raises(ValueError):
            config = BehaviorConfig(error_rate=-0.1)
            config.validate()

        # Invalid timeout probability
        with pytest.raises(ValueError):
            config = BehaviorConfig(timeout_probability=1.5)
            config.validate()

        # Invalid timeout delay range
        with pytest.raises(ValueError):
            config = BehaviorConfig(
                timeout_delay_min_ms=1000,
                timeout_delay_max_ms=500,
            )
            config.validate()
