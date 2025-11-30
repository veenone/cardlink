"""Initial database schema.

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000

This migration creates the initial database schema with all tables:
- devices: Phone and modem device configuration
- card_profiles: UICC card profiles with PSK credentials
- ota_sessions: OTA session records
- comm_logs: APDU communication logs
- test_results: Test execution results
- settings: Application settings
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # =========================================================================
    # Devices table
    # =========================================================================
    op.create_table(
        "devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column(
            "device_type",
            sa.Enum("phone", "modem", name="devicetype"),
            nullable=False,
        ),
        sa.Column("manufacturer", sa.String(64), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("firmware_version", sa.String(64), nullable=True),
        sa.Column("imei", sa.String(20), nullable=True),
        sa.Column("imsi", sa.String(20), nullable=True),
        sa.Column("iccid", sa.String(22), nullable=True),
        sa.Column("connection_settings", sa.JSON(), nullable=True),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index("idx_device_type", "devices", ["device_type"])
    op.create_index("idx_device_iccid", "devices", ["iccid"])
    op.create_index("idx_device_last_seen", "devices", ["last_seen"])
    op.create_index("idx_device_active", "devices", ["is_active"])

    # =========================================================================
    # Card Profiles table
    # =========================================================================
    op.create_table(
        "card_profiles",
        sa.Column("iccid", sa.String(22), primary_key=True),
        sa.Column("imsi", sa.String(20), nullable=True),
        sa.Column("card_type", sa.String(20), nullable=False, default="UICC"),
        sa.Column("atr", sa.String(128), nullable=True),
        sa.Column("psk_identity", sa.String(128), nullable=True),
        sa.Column("psk_key_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("admin_url", sa.String(255), nullable=True),
        sa.Column("trigger_config", sa.JSON(), nullable=True),
        sa.Column("bip_config", sa.JSON(), nullable=True),
        sa.Column("security_domains", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index("idx_card_type", "card_profiles", ["card_type"])
    op.create_index("idx_card_psk_identity", "card_profiles", ["psk_identity"])
    op.create_index("idx_card_imsi", "card_profiles", ["imsi"])

    # =========================================================================
    # OTA Sessions table
    # =========================================================================
    op.create_table(
        "ota_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "device_id",
            sa.String(64),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "card_iccid",
            sa.String(22),
            sa.ForeignKey("card_profiles.iccid", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_type", sa.String(20), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "active", "completed", "failed", "timeout",
                name="sessionstatus"
            ),
            nullable=False,
            default="pending",
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tls_cipher_suite", sa.String(64), nullable=True),
        sa.Column("tls_psk_identity", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index("idx_session_device", "ota_sessions", ["device_id"])
    op.create_index("idx_session_card", "ota_sessions", ["card_iccid"])
    op.create_index("idx_session_status", "ota_sessions", ["status"])
    op.create_index("idx_session_created", "ota_sessions", ["created_at"])
    op.create_index("idx_session_started", "ota_sessions", ["started_at"])

    # =========================================================================
    # Communication Logs table
    # =========================================================================
    op.create_table(
        "comm_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("ota_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("raw_data", sa.Text(), nullable=False),
        sa.Column("decoded_data", sa.Text(), nullable=True),
        sa.Column("status_word", sa.String(4), nullable=True),
        sa.Column("status_message", sa.String(128), nullable=True),
    )

    op.create_index("idx_log_session", "comm_logs", ["session_id"])
    op.create_index("idx_log_timestamp", "comm_logs", ["timestamp"])
    op.create_index("idx_log_direction", "comm_logs", ["direction"])
    op.create_index("idx_log_status_word", "comm_logs", ["status_word"])

    # =========================================================================
    # Test Results table
    # =========================================================================
    op.create_table(
        "test_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False, index=True),
        sa.Column("suite_name", sa.String(128), nullable=False),
        sa.Column("test_name", sa.String(256), nullable=False),
        sa.Column(
            "device_id",
            sa.String(64),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "card_iccid",
            sa.String(22),
            sa.ForeignKey("card_profiles.iccid", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("passed", "failed", "skipped", "error", name="teststatus"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("assertions", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index("idx_test_run", "test_results", ["run_id"])
    op.create_index("idx_test_suite", "test_results", ["suite_name"])
    op.create_index("idx_test_status", "test_results", ["status"])
    op.create_index("idx_test_created", "test_results", ["created_at"])
    op.create_index("idx_test_device", "test_results", ["device_id"])
    op.create_index("idx_test_card", "test_results", ["card_iccid"])

    # =========================================================================
    # Settings table
    # =========================================================================
    op.create_table(
        "settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(256), nullable=True),
        sa.Column("category", sa.String(64), nullable=False, default="general"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index("idx_setting_category", "settings", ["category"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("settings")
    op.drop_table("test_results")
    op.drop_table("comm_logs")
    op.drop_table("ota_sessions")
    op.drop_table("card_profiles")
    op.drop_table("devices")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS teststatus")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
    op.execute("DROP TYPE IF EXISTS devicetype")
