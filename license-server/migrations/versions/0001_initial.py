"""Create initial WARAKA license tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "licenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("serial_hash", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="pro"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("serial_hash"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_licenses_serial_hash", "licenses", ["serial_hash"], unique=True)
    op.create_index("ix_licenses_email", "licenses", ["email"], unique=True)
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("license_id", sa.Integer(), sa.ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=False, server_default="Windows PC"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("license_id", "device_id", name="uq_license_device"),
    )
    op.create_index("ix_devices_license_id", "devices", ["license_id"])
    op.create_table(
        "activation_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("license_id", sa.Integer(), sa.ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activation_codes_license_id", "activation_codes", ["license_id"])
    op.create_index("ix_activation_codes_expires_at", "activation_codes", ["expires_at"])

def downgrade():
    op.drop_index("ix_activation_codes_expires_at", table_name="activation_codes")
    op.drop_index("ix_activation_codes_license_id", table_name="activation_codes")
    op.drop_table("activation_codes")
    op.drop_index("ix_devices_license_id", table_name="devices")
    op.drop_table("devices")
    op.drop_index("ix_licenses_email", table_name="licenses")
    op.drop_index("ix_licenses_serial_hash", table_name="licenses")
    op.drop_table("licenses")
