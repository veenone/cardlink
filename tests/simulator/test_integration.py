"""Integration tests for Mobile Simulator.

These tests verify the complete simulator workflow including TLS connection,
HTTP Admin protocol, and APDU exchanges.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from cardlink.simulator import (
    MobileSimulator,
    SimulatorConfig,
    ConnectionState,
    BehaviorMode,
    BehaviorConfig,
)


class TestSimulatorIntegration:
    """Integration tests for complete simulator workflow."""

    @pytest.mark.asyncio
    async def test_simulator_lifecycle(self, default_config):
        """Test complete simulator lifecycle: connect, run, disconnect."""
        simulator = MobileSimulator(default_config)

        # Initial state should be IDLE
        assert simulator.state == ConnectionState.IDLE

        # Mock TLS and HTTP components for testing
        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls, \
             patch("cardlink.simulator.client.HTTPAdminClient") as mock_http_cls:

            # Setup mocks
            mock_tls = AsyncMock()
            mock_tls.connect = AsyncMock(return_value=Mock(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
                psk_identity="test_card",
                protocol_version="TLSv1.2",
                handshake_duration_ms=45.0,
            ))
            mock_tls_cls.return_value = mock_tls

            mock_http = Mock()
            # Simulate initial request returning a SELECT ISD command
            select_cmd = bytes.fromhex("00A4040007A000000151000000")
            mock_http.initial_request = AsyncMock(return_value=select_cmd)
            # Simulate server returning 204 (session complete) after first response
            mock_http.send_response = AsyncMock(return_value=None)
            mock_http_cls.return_value = mock_http

            # Connect
            success = await simulator.connect()
            assert success
            assert simulator.state == ConnectionState.CONNECTED

            # Run session
            result = await simulator.run_session()
            assert result.success
            assert result.apdu_count > 0
            assert simulator.state == ConnectionState.CONNECTED

            # Disconnect
            await simulator.disconnect()
            assert simulator.state == ConnectionState.IDLE

    @pytest.mark.asyncio
    async def test_run_complete_session(self, default_config):
        """Test run_complete_session convenience method."""
        simulator = MobileSimulator(default_config)

        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls, \
             patch("cardlink.simulator.client.HTTPAdminClient") as mock_http_cls:

            # Setup mocks
            mock_tls = AsyncMock()
            mock_tls.connect = AsyncMock(return_value=Mock(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
                psk_identity="test_card",
                protocol_version="TLSv1.2",
            ))
            mock_tls.close = AsyncMock()
            mock_tls_cls.return_value = mock_tls

            mock_http = Mock()
            select_cmd = bytes.fromhex("00A4040007A000000151000000")
            mock_http.initial_request = AsyncMock(return_value=select_cmd)
            mock_http.send_response = AsyncMock(return_value=None)
            mock_http_cls.return_value = mock_http

            # Run complete session
            result = await simulator.run_complete_session()

            # Should have connected, run session, and disconnected
            assert result.success
            assert simulator.state == ConnectionState.IDLE
            mock_tls.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_retry_on_failure(self):
        """Test connection retry logic on transient failures."""
        from cardlink.simulator import ConnectionError as SimConnectionError

        config = SimulatorConfig(
            retry_count=2,
            retry_backoff=[0.01, 0.02],  # Fast retries for testing
        )
        simulator = MobileSimulator(config)

        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls:
            mock_tls = AsyncMock()

            # Fail first two attempts, succeed on third
            mock_tls.connect = AsyncMock(
                side_effect=[
                    SimConnectionError("Connection refused"),
                    SimConnectionError("Connection refused"),
                    Mock(
                        cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
                        psk_identity="test_card",
                    ),
                ]
            )
            mock_tls_cls.return_value = mock_tls

            # Should eventually succeed
            success = await simulator.connect()
            assert success
            assert simulator.state == ConnectionState.CONNECTED

            # Should have tried 3 times
            assert mock_tls.connect.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_handshake_failure(self):
        """Test no retry on PSK handshake failure."""
        config = SimulatorConfig(retry_count=3)
        simulator = MobileSimulator(config)

        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls:
            from cardlink.simulator import HandshakeError

            mock_tls = AsyncMock()
            mock_tls.connect = AsyncMock(
                side_effect=HandshakeError("PSK identity not found")
            )
            mock_tls_cls.return_value = mock_tls

            # Should fail immediately without retry
            success = await simulator.connect()
            assert not success
            assert simulator.state == ConnectionState.ERROR

            # Should have tried only once (no retries on auth failure)
            assert mock_tls.connect.call_count == 1

    @pytest.mark.asyncio
    async def test_error_injection_mode(self):
        """Test simulator with error injection enabled."""
        config = SimulatorConfig(
            behavior=BehaviorConfig(
                mode=BehaviorMode.ERROR,
                error_rate=1.0,  # Always inject errors
                error_codes=["6A82"],
            )
        )
        simulator = MobileSimulator(config)

        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls, \
             patch("cardlink.simulator.client.HTTPAdminClient") as mock_http_cls:

            mock_tls = AsyncMock()
            mock_tls.connect = AsyncMock(return_value=Mock(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
                psk_identity="test_card",
            ))
            mock_tls_cls.return_value = mock_tls

            mock_http = Mock()
            select_cmd = bytes.fromhex("00A4040007A000000151000000")
            mock_http.initial_request = AsyncMock(return_value=select_cmd)
            mock_http.send_response = AsyncMock(return_value=None)
            mock_http_cls.return_value = mock_http

            await simulator.connect()
            result = await simulator.run_session()

            # Should complete but with error responses
            assert result.success
            assert len(result.exchanges) > 0

            # All responses should be errors (6A82)
            for exchange in result.exchanges:
                assert exchange.sw == "6A82"

    @pytest.mark.asyncio
    async def test_statistics_collection(self, default_config):
        """Test statistics are collected during session."""
        simulator = MobileSimulator(default_config)

        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls, \
             patch("cardlink.simulator.client.HTTPAdminClient") as mock_http_cls:

            mock_tls = AsyncMock()
            mock_tls.connect = AsyncMock(return_value=Mock(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
                psk_identity="test_card",
            ))
            mock_tls_cls.return_value = mock_tls

            mock_http = Mock()
            # Return 3 commands
            commands = [
                bytes.fromhex("00A4040007A000000151000000"),
                bytes.fromhex("80F28000024F00"),
                None,  # Session complete
            ]
            mock_http.initial_request = AsyncMock(return_value=commands[0])
            mock_http.send_response = AsyncMock(side_effect=commands[1:])
            mock_http_cls.return_value = mock_http

            await simulator.connect()
            result = await simulator.run_session()

            stats = simulator.get_statistics()

            # Verify statistics
            assert stats.connections_attempted == 1
            assert stats.connections_succeeded == 1
            assert stats.sessions_completed == 1
            assert stats.total_apdus_received == 2
            assert stats.total_apdus_sent == 2
            assert stats.avg_connection_time_ms > 0

    @pytest.mark.asyncio
    async def test_context_manager(self, default_config):
        """Test simulator as async context manager."""
        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls:
            mock_tls = AsyncMock()
            mock_tls.connect = AsyncMock(return_value=Mock(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
                psk_identity="test_card",
            ))
            mock_tls.close = AsyncMock()
            mock_tls_cls.return_value = mock_tls

            async with MobileSimulator(default_config) as simulator:
                assert simulator.state == ConnectionState.CONNECTED
                mock_tls.connect.assert_called_once()

            # Should disconnect on exit
            assert simulator.state == ConnectionState.IDLE
            mock_tls.close.assert_called_once()


@pytest.mark.asyncio
class TestMultipleSimulators:
    """Test running multiple simulators concurrently."""

    async def test_parallel_simulators(self, default_config):
        """Test multiple simulators running in parallel."""
        with patch("cardlink.simulator.client.PSKTLSClient") as mock_tls_cls, \
             patch("cardlink.simulator.client.HTTPAdminClient") as mock_http_cls:

            def create_mocks():
                mock_tls = AsyncMock()
                mock_tls.connect = AsyncMock(return_value=Mock(
                    cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
                    psk_identity="test_card",
                ))
                mock_tls.close = AsyncMock()

                mock_http = Mock()
                select_cmd = bytes.fromhex("00A4040007A000000151000000")
                mock_http.initial_request = AsyncMock(return_value=select_cmd)
                mock_http.send_response = AsyncMock(return_value=None)

                return mock_tls, mock_http

            # Create multiple simulators
            simulators = [MobileSimulator(default_config) for _ in range(3)]

            # Setup individual mocks for each simulator
            mock_tls_cls.side_effect = [create_mocks()[0] for _ in range(3)]
            mock_http_cls.side_effect = [create_mocks()[1] for _ in range(3)]

            # Run all simulators in parallel
            tasks = [sim.run_complete_session() for sim in simulators]
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(r.success for r in results)
            assert all(r.apdu_count > 0 for r in results)
