"""Unit tests for database repositories."""

import pytest
from datetime import datetime, timedelta

from cardlink.database import (
    DatabaseConfig,
    DatabaseManager,
    Device,
    DeviceType,
    CardProfile,
    OTASession,
    SessionStatus,
    CommLog,
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


@pytest.fixture
def populated_db(db_manager):
    """Create a database with sample data."""
    with UnitOfWork(db_manager) as uow:
        # Create devices
        phone1 = Device(
            id="phone1",
            name="Test Phone 1",
            device_type=DeviceType.PHONE,
            is_active=True,
        )
        phone2 = Device(
            id="phone2",
            name="Test Phone 2",
            device_type=DeviceType.PHONE,
            is_active=False,
        )
        modem1 = Device(
            id="/dev/ttyUSB0",
            name="Modem 1",
            device_type=DeviceType.MODEM,
            is_active=True,
        )
        uow.devices.add_all([phone1, phone2, modem1])

        # Create cards
        card1 = CardProfile(
            iccid="89012345678901234567",
            psk_identity="card_001",
        )
        card2 = CardProfile(
            iccid="89012345678901234568",
            psk_identity="card_002",
        )
        uow.cards.add_all([card1, card2])

        # Create sessions
        session1 = OTASession(device_id="phone1", card_iccid=card1.iccid)
        session1.start()
        session1.complete()

        session2 = OTASession(device_id="phone1", card_iccid=card1.iccid)
        session2.start()
        session2.fail("ERROR", "Test error")

        uow.sessions.add_all([session1, session2])

        uow.commit()

    return db_manager


class TestDeviceRepository:
    """Test DeviceRepository."""

    def test_find_phones(self, populated_db):
        """Test finding phone devices."""
        with UnitOfWork(populated_db) as uow:
            phones = uow.devices.find_phones()
            assert len(phones) == 2

    def test_find_modems(self, populated_db):
        """Test finding modem devices."""
        with UnitOfWork(populated_db) as uow:
            modems = uow.devices.find_modems()
            assert len(modems) == 1
            assert modems[0].id == "/dev/ttyUSB0"

    def test_find_active(self, populated_db):
        """Test finding active devices."""
        with UnitOfWork(populated_db) as uow:
            active = uow.devices.find_active()
            assert len(active) == 2  # phone1 and modem1

    def test_search(self, populated_db):
        """Test searching devices."""
        with UnitOfWork(populated_db) as uow:
            results = uow.devices.search("Phone")
            assert len(results) == 2

            results = uow.devices.search("Modem")
            assert len(results) == 1

    def test_activate_deactivate(self, populated_db):
        """Test activating and deactivating devices."""
        with UnitOfWork(populated_db) as uow:
            # Deactivate
            success = uow.devices.deactivate("phone1")
            assert success

            uow.commit()

            device = uow.devices.get("phone1")
            assert not device.is_active

            # Activate
            success = uow.devices.activate("phone1")
            assert success

            uow.commit()

            device = uow.devices.get("phone1")
            assert device.is_active

    def test_get_stats(self, populated_db):
        """Test getting device statistics."""
        with UnitOfWork(populated_db) as uow:
            stats = uow.devices.get_stats()
            assert stats["total"] == 3
            assert stats["phones"] == 2
            assert stats["modems"] == 1
            assert stats["active"] == 2


class TestCardRepository:
    """Test CardRepository."""

    def test_find_by_psk_identity(self, populated_db):
        """Test finding card by PSK identity."""
        with UnitOfWork(populated_db) as uow:
            card = uow.cards.find_by_psk_identity("card_001")
            assert card is not None
            assert card.iccid == "89012345678901234567"

    def test_find_with_psk(self, populated_db):
        """Test finding cards with PSK configured."""
        with UnitOfWork(populated_db) as uow:
            # Add a card without PSK
            card = CardProfile(iccid="89012345678901234569")
            uow.cards.create(card)
            uow.commit()

            # Cards with PSK identity but no encrypted key
            # shouldn't be found by find_with_psk
            cards = uow.cards.find_with_psk()
            assert len(cards) == 0  # No cards have encrypted PSK

    def test_get_psk_identities(self, populated_db):
        """Test getting all PSK identities."""
        with UnitOfWork(populated_db) as uow:
            identities = uow.cards.get_psk_identities()
            assert "card_001" in identities
            assert "card_002" in identities

    def test_search(self, populated_db):
        """Test searching cards."""
        with UnitOfWork(populated_db) as uow:
            results = uow.cards.search("89012345678901234567")
            assert len(results) == 1


class TestSessionRepository:
    """Test SessionRepository."""

    def test_find_by_status(self, populated_db):
        """Test finding sessions by status."""
        with UnitOfWork(populated_db) as uow:
            completed = uow.sessions.find_completed()
            assert len(completed) == 1

            failed = uow.sessions.find_failed()
            assert len(failed) == 1

    def test_find_by_device(self, populated_db):
        """Test finding sessions by device."""
        with UnitOfWork(populated_db) as uow:
            sessions = uow.sessions.find_by_device("phone1")
            assert len(sessions) == 2

    def test_find_with_errors(self, populated_db):
        """Test finding sessions with errors."""
        with UnitOfWork(populated_db) as uow:
            sessions = uow.sessions.find_with_errors()
            assert len(sessions) == 1
            assert sessions[0].error_code == "ERROR"

    def test_get_stats(self, populated_db):
        """Test getting session statistics."""
        with UnitOfWork(populated_db) as uow:
            stats = uow.sessions.get_stats()
            assert stats["total"] == 2
            assert stats["completed"] == 1
            assert stats["failed"] == 1


class TestLogRepository:
    """Test LogRepository."""

    def test_log_command_response(self, db_manager):
        """Test logging commands and responses."""
        with UnitOfWork(db_manager) as uow:
            session = OTASession()
            uow.sessions.create(session)
            uow.commit()

            # Log command
            cmd = uow.logs.log_command(session.id, "00A4040007A0000000041010")

            # Log response
            resp = uow.logs.log_response(session.id, "9000", latency_ms=15.0)

            uow.commit()

            logs = uow.logs.find_by_session(session.id)
            assert len(logs) == 2

            commands = uow.logs.find_commands(session.id)
            assert len(commands) == 1

            responses = uow.logs.find_responses(session.id)
            assert len(responses) == 1

    def test_get_session_summary(self, db_manager):
        """Test getting session log summary."""
        with UnitOfWork(db_manager) as uow:
            session = OTASession()
            uow.sessions.create(session)
            uow.commit()

            # Add some logs
            uow.logs.log_command(session.id, "00A40400")
            uow.logs.log_response(session.id, "9000", latency_ms=10.0)
            uow.logs.log_command(session.id, "00B00000")
            uow.logs.log_response(session.id, "6A82", latency_ms=5.0)
            uow.commit()

            summary = uow.logs.get_session_summary(session.id)
            assert summary["total_logs"] == 4
            assert summary["command_count"] == 2
            assert summary["response_count"] == 2
            assert summary["success_count"] == 1
            assert summary["error_count"] == 1


class TestTestRepository:
    """Test TestRepository."""

    def test_find_by_run(self, db_manager):
        """Test finding tests by run ID."""
        with UnitOfWork(db_manager) as uow:
            run_id = "test_run_001"

            result1 = TestResult.create(run_id, "Suite1", "test_a")
            result1.pass_test()

            result2 = TestResult.create(run_id, "Suite1", "test_b")
            result2.fail_test()

            uow.tests.add_all([result1, result2])
            uow.commit()

            results = uow.tests.find_by_run(run_id)
            assert len(results) == 2

    def test_get_run_stats(self, db_manager):
        """Test getting run statistics."""
        with UnitOfWork(db_manager) as uow:
            run_id = "test_run_002"

            for i in range(5):
                result = TestResult.create(run_id, "Suite", f"test_{i}")
                if i < 3:
                    result.pass_test()
                else:
                    result.fail_test()
                uow.tests.add(result)

            uow.commit()

            stats = uow.tests.get_run_stats(run_id)
            assert stats["total"] == 5
            assert stats["passed"] == 3
            assert stats["failed"] == 2


class TestSettingRepository:
    """Test SettingRepository."""

    def test_get_set_value(self, db_manager):
        """Test getting and setting values."""
        with UnitOfWork(db_manager) as uow:
            # Set value
            uow.settings.set_value("server.port", 8443, category="server")
            uow.commit()

            # Get value
            value = uow.settings.get_value("server.port")
            assert value == 8443

            # Get default for missing
            value = uow.settings.get_value("missing", default=1234)
            assert value == 1234

    def test_typed_getters(self, db_manager):
        """Test typed getter methods."""
        with UnitOfWork(db_manager) as uow:
            uow.settings.set_value("int_val", 42)
            uow.settings.set_value("float_val", 3.14)
            uow.settings.set_value("bool_val", True)
            uow.settings.set_value("list_val", [1, 2, 3])
            uow.commit()

            assert uow.settings.get_int("int_val") == 42
            assert abs(uow.settings.get_float("float_val") - 3.14) < 0.01
            assert uow.settings.get_bool("bool_val") is True
            assert uow.settings.get_list("list_val") == [1, 2, 3]

    def test_find_by_category(self, db_manager):
        """Test finding settings by category."""
        with UnitOfWork(db_manager) as uow:
            uow.settings.set_value("server.host", "localhost", category="server")
            uow.settings.set_value("server.port", 8443, category="server")
            uow.settings.set_value("log.level", "INFO", category="logging")
            uow.commit()

            server_settings = uow.settings.find_by_category("server")
            assert len(server_settings) == 2

    def test_get_all_as_dict(self, db_manager):
        """Test getting all settings as dictionary."""
        with UnitOfWork(db_manager) as uow:
            uow.settings.set_value("a", 1)
            uow.settings.set_value("b", 2)
            uow.commit()

            all_settings = uow.settings.get_all_as_dict()
            assert all_settings["a"] == 1
            assert all_settings["b"] == 2


class TestPagination:
    """Test pagination functionality."""

    def test_paginate_devices(self, db_manager):
        """Test paginating devices."""
        with UnitOfWork(db_manager) as uow:
            # Create 25 devices
            for i in range(25):
                device = Device(
                    id=f"device_{i:03d}",
                    device_type=DeviceType.PHONE,
                )
                uow.devices.add(device)
            uow.commit()

            # Page 1
            page = uow.devices.paginate(page=1, per_page=10)
            assert len(page.items) == 10
            assert page.total == 25
            assert page.pages == 3
            assert page.has_next
            assert not page.has_prev

            # Page 2
            page = uow.devices.paginate(page=2, per_page=10)
            assert len(page.items) == 10
            assert page.has_next
            assert page.has_prev

            # Page 3 (last)
            page = uow.devices.paginate(page=3, per_page=10)
            assert len(page.items) == 5
            assert not page.has_next
            assert page.has_prev
