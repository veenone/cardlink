"""Unit tests for database models."""

import pytest
from datetime import datetime

from cardlink.database import (
    DatabaseConfig,
    DatabaseManager,
    Device,
    DeviceType,
    CardProfile,
    OTASession,
    SessionStatus,
    CommLog,
    CommDirection,
    TestResult,
    TestStatus,
    Setting,
    UnitOfWork,
)


@pytest.fixture
def db_manager():
    """Create a test database manager with in-memory SQLite."""
    config = DatabaseConfig.for_testing()
    manager = DatabaseManager(config)
    manager.initialize()
    manager.create_tables()
    yield manager
    manager.close()


class TestDevice:
    """Test Device model."""

    def test_create_phone_device(self, db_manager):
        """Test creating a phone device."""
        with UnitOfWork(db_manager) as uow:
            device = Device(
                id="RF8M33XXXXX",
                name="Test Phone",
                device_type=DeviceType.PHONE,
                manufacturer="Samsung",
                model="Galaxy S21",
            )
            uow.devices.create(device)
            uow.commit()

            # Retrieve and verify
            retrieved = uow.devices.get("RF8M33XXXXX")
            assert retrieved is not None
            assert retrieved.name == "Test Phone"
            assert retrieved.is_phone
            assert not retrieved.is_modem
            assert retrieved.display_name == "Test Phone"

    def test_create_modem_device(self, db_manager):
        """Test creating a modem device."""
        with UnitOfWork(db_manager) as uow:
            device = Device(
                id="/dev/ttyUSB0",
                name="Test Modem",
                device_type=DeviceType.MODEM,
            )
            uow.devices.create(device)
            uow.commit()

            retrieved = uow.devices.get("/dev/ttyUSB0")
            assert retrieved.is_modem
            assert not retrieved.is_phone

    def test_device_update_last_seen(self, db_manager):
        """Test updating device last seen timestamp."""
        with UnitOfWork(db_manager) as uow:
            device = Device(
                id="test_device",
                device_type=DeviceType.PHONE,
            )
            uow.devices.create(device)
            uow.commit()

            # Update last seen
            device.update_last_seen()
            uow.commit()

            assert device.last_seen is not None

    def test_device_connection_settings(self, db_manager):
        """Test device connection settings."""
        with UnitOfWork(db_manager) as uow:
            device = Device(
                id="test_device",
                device_type=DeviceType.MODEM,
            )
            device.set_connection_setting("baud_rate", 115200)
            device.set_connection_setting("parity", "N")
            uow.devices.create(device)
            uow.commit()

            assert device.get_connection_setting("baud_rate") == 115200
            assert device.get_connection_setting("unknown", "default") == "default"


class TestCardProfile:
    """Test CardProfile model."""

    def test_create_card_profile(self, db_manager):
        """Test creating a card profile."""
        with UnitOfWork(db_manager) as uow:
            card = CardProfile(
                iccid="89012345678901234567",
                imsi="123456789012345",
                card_type="UICC",
                psk_identity="test_card_001",
            )
            uow.cards.create(card)
            uow.commit()

            retrieved = uow.cards.get("89012345678901234567")
            assert retrieved is not None
            assert retrieved.imsi == "123456789012345"
            assert retrieved.short_iccid == "...01234567"

    def test_card_trigger_config(self, db_manager):
        """Test card trigger configuration."""
        with UnitOfWork(db_manager) as uow:
            card = CardProfile(iccid="89012345678901234567")
            card.set_trigger_config("sms", port=2948)
            uow.cards.create(card)
            uow.commit()

            assert card.get_trigger_type() == "sms"
            assert card.trigger_config["port"] == 2948

    def test_card_bip_config(self, db_manager):
        """Test card BIP configuration."""
        with UnitOfWork(db_manager) as uow:
            card = CardProfile(iccid="89012345678901234567")
            card.set_bip_config(channel=1, buffer_size=2048)
            uow.cards.create(card)
            uow.commit()

            assert card.bip_config["channel"] == 1
            assert card.bip_config["buffer_size"] == 2048


class TestOTASession:
    """Test OTASession model."""

    def test_create_session(self, db_manager):
        """Test creating an OTA session."""
        with UnitOfWork(db_manager) as uow:
            session = OTASession(session_type="triggered")
            uow.sessions.create(session)
            uow.commit()

            assert session.id is not None
            assert session.is_pending
            assert not session.is_finished

    def test_session_lifecycle(self, db_manager):
        """Test session lifecycle methods."""
        with UnitOfWork(db_manager) as uow:
            session = OTASession()
            uow.sessions.create(session)

            # Start session
            session.start()
            assert session.is_active
            assert session.started_at is not None

            # Complete session
            session.complete()
            assert session.is_completed
            assert session.is_finished
            assert session.ended_at is not None
            assert session.duration_ms is not None

            uow.commit()

    def test_session_failure(self, db_manager):
        """Test session failure."""
        with UnitOfWork(db_manager) as uow:
            session = OTASession()
            session.start()
            session.fail("CONNECTION_ERROR", "Failed to connect")

            assert session.is_failed
            assert session.error_code == "CONNECTION_ERROR"
            assert session.error_message == "Failed to connect"

            uow.sessions.create(session)
            uow.commit()


class TestCommLog:
    """Test CommLog model."""

    def test_create_command_log(self, db_manager):
        """Test creating a command log."""
        with UnitOfWork(db_manager) as uow:
            session = OTASession()
            uow.sessions.create(session)
            uow.commit()

            log = CommLog.create_command(
                session_id=session.id,
                raw_data="00A4040007A0000000041010",
                decoded_data="SELECT ISD",
            )
            uow.logs.create(log)
            uow.commit()

            assert log.is_command
            assert not log.is_response
            assert log.data_length == 12

    def test_create_response_log(self, db_manager):
        """Test creating a response log with status word."""
        with UnitOfWork(db_manager) as uow:
            session = OTASession()
            uow.sessions.create(session)
            uow.commit()

            log = CommLog.create_response(
                session_id=session.id,
                raw_data="9000",
                latency_ms=15.5,
            )
            uow.logs.create(log)
            uow.commit()

            assert log.is_response
            assert log.status_word == "9000"
            assert log.is_success
            assert log.status_message == "Success"
            assert log.latency_ms == 15.5

    def test_status_word_decoding(self):
        """Test status word decoding."""
        assert CommLog.decode_status_word("9000") == "Success"
        assert CommLog.decode_status_word("6A82") == "File not found"
        assert CommLog.decode_status_word("6D00") == "INS not supported"
        assert "Unknown" in CommLog.decode_status_word("FFFF")


class TestTestResult:
    """Test TestResult model."""

    def test_create_test_result(self, db_manager):
        """Test creating a test result."""
        with UnitOfWork(db_manager) as uow:
            result = TestResult.create(
                run_id="run_123",
                suite_name="OTA Tests",
                test_name="test_select_isd",
            )
            result.add_assertion("Status word is 9000", True)
            result.pass_test()

            uow.tests.create(result)
            uow.commit()

            assert result.is_passed
            assert result.assertion_count == 1
            assert result.failed_assertion_count == 0
            assert result.duration_ms is not None

    def test_failed_test_result(self, db_manager):
        """Test failed test result."""
        with UnitOfWork(db_manager) as uow:
            result = TestResult.create(
                run_id="run_123",
                suite_name="OTA Tests",
                test_name="test_install",
            )
            result.add_assertion("Installation successful", False, expected="9000", actual="6A80")
            result.fail_test("Assertion failed")

            uow.tests.create(result)
            uow.commit()

            assert result.is_failed
            assert result.failed_assertion_count == 1
            assert result.error_message == "Assertion failed"


class TestSetting:
    """Test Setting model."""

    def test_create_setting(self, db_manager):
        """Test creating a setting."""
        with UnitOfWork(db_manager) as uow:
            setting = Setting(
                key="server.port",
                value=8443,
                category="server",
                description="Server port",
            )
            uow.settings.create(setting)
            uow.commit()

            retrieved = uow.settings.get("server.port")
            assert retrieved.as_int() == 8443

    def test_setting_types(self, db_manager):
        """Test setting type conversions."""
        with UnitOfWork(db_manager) as uow:
            # Boolean
            s1 = Setting(key="enabled", value=True)
            uow.settings.create(s1)

            # List
            s2 = Setting(key="hosts", value=["a", "b", "c"])
            uow.settings.create(s2)

            # Dict
            s3 = Setting(key="config", value={"nested": True})
            uow.settings.create(s3)

            uow.commit()

            assert uow.settings.get("enabled").as_bool() is True
            assert uow.settings.get("hosts").as_list() == ["a", "b", "c"]
            assert uow.settings.get("config").as_dict()["nested"] is True
