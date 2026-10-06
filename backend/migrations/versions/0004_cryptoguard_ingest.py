"""Durable tenant-scoped CryptoGuard agent enrollment and telemetry."""
from alembic import op
import sqlalchemy as sa
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('cryptoguard_agents',
        sa.Column('tenant_id',sa.String(64),primary_key=True,server_default='lab'),sa.Column('agent_id',sa.String(36),primary_key=True),
        sa.Column('host_id',sa.String(128),nullable=False),sa.Column('platform',sa.String(16),nullable=False),
        sa.Column('token_hash',sa.String(64),nullable=False,unique=True),sa.Column('enabled',sa.Boolean(),nullable=False),
        sa.Column('enrolled_at',sa.DateTime(timezone=True),nullable=False),sa.Column('last_received_at',sa.DateTime(timezone=True)),sa.Column('last_observed_at',sa.DateTime(timezone=True)))
    op.create_index('ix_cryptoguard_agents_tenant_id','cryptoguard_agents',['tenant_id'])
    op.create_table('cryptoguard_enrollments',sa.Column('tenant_id',sa.String(64),nullable=False,server_default='lab'),
        sa.Column('token_hash',sa.String(64),primary_key=True),sa.Column('agent_id',sa.String(36),nullable=False),sa.Column('platform',sa.String(16),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('used_at',sa.DateTime(timezone=True)))
    op.create_index('ix_cryptoguard_enrollments_tenant_id','cryptoguard_enrollments',['tenant_id'])
    op.create_table('cryptoguard_events',sa.Column('tenant_id',sa.String(64),primary_key=True,server_default='lab'),
        sa.Column('agent_id',sa.String(36),primary_key=True),sa.Column('event_uid',sa.String(36),primary_key=True),
        sa.Column('sequence',sa.Integer(),nullable=False),sa.Column('event_type',sa.String(16),nullable=False),
        sa.Column('observed_at',sa.DateTime(timezone=True),nullable=False),sa.Column('received_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('payload_sha256',sa.String(64),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),
        sa.ForeignKeyConstraint(['tenant_id','agent_id'],['cryptoguard_agents.tenant_id','cryptoguard_agents.agent_id']),
        sa.UniqueConstraint('tenant_id','agent_id','sequence',name='uq_cg_agent_sequence'))
    op.create_index('ix_cryptoguard_events_observed_at','cryptoguard_events',['observed_at'])
    op.create_index('ix_cryptoguard_events_tenant_id','cryptoguard_events',['tenant_id'])

def downgrade():
    op.drop_table('cryptoguard_events');op.drop_table('cryptoguard_enrollments');op.drop_table('cryptoguard_agents')
