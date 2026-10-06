from datetime import timedelta
from uuid import uuid4
import pytest

from sqlalchemy.orm import Session

from app.cryptoguard.models import CryptoGuardAgent, CryptoGuardEvent
from app.db.models import Event, Incident
from tests.conftest import T0, auth, mk_event


def report(client, **params):
    response = client.get('/v1/reports/soc-summary', headers=auth('v'), params={
        'from': T0.isoformat(), 'to': (T0 + timedelta(hours=1)).isoformat(), **params})
    assert response.status_code == 200, response.text
    return response.json()


def add_event(session, uid, **kw):
    session.add(Event(**mk_event(uid, **kw).model_dump()))


def test_empty_report_is_unavailable_not_zero(client):
    body = report(client)
    assert body['tenant'] == 'lab'
    assert body['alerts']['count'] is None
    assert body['incidents']['open_count'] is None
    assert body['identity']['event_count'] is None
    assert body['network']['status'] == 'unavailable'
    assert body['honeypots']['event_count'] is None
    assert body['cryptoguard']['status'] == 'not_configured'


def test_range_real_only_distributions_and_incidents(client, session):
    add_event(session, 'start', event_type='endpoint_alert', summary='Authentication failure', prio='high')
    add_event(session, 'network', sensor='suricata', event_type='network_alert', minutes=10, prio='critical')
    add_event(session, 'honey', sensor='cowrie', event_type='login', minutes=15, prio='low')
    add_event(session, 'resource', sensor='cryptoguard', event_type='telemetry', minutes=20)
    add_event(session, 'test-event', minutes=25, execution_mode='TEST', is_test=True)
    add_event(session, 'before', minutes=-1)
    add_event(session, 'exclusive-end', minutes=60)
    for status in ('NEW', 'CONTAINED', 'RESOLVED', 'CLOSED'):
        session.add(Incident(opened_at=T0, last_seen=T0, status=status, priority='high', title=status))
    session.add(Incident(opened_at=T0, last_seen=T0, status='NEW', priority='critical', title='test', execution_mode='TEST'))
    session.commit()
    body = report(client)
    assert body['alerts']['count'] == 3
    assert body['alerts']['severity_distribution'] == {'high': 1, 'critical': 1, 'low': 1}
    assert body['alerts']['source_distribution'] == {'wazuh': 1, 'suricata': 1, 'cowrie': 1}
    assert len(body['alerts']['high_priority']) == 2
    assert body['incidents']['count'] == 4
    assert body['incidents']['open_count'] == 2
    assert len(body['incidents']['items']) == 4
    assert body['identity']['event_count'] == 1
    assert body['network']['event_count'] == 1
    assert body['honeypots']['event_count'] == 1


def test_totals_are_not_limited_to_preview(client, session):
    for i in range(31):
        add_event(session, str(i), minutes=i)
    session.commit()
    body = report(client)
    assert body['alerts']['count'] == 31
    assert len(body['alerts']['latest']) == 25
    assert sum(body['alerts']['severity_distribution'].values()) == 31


def test_tenant_isolation(client, session, engine):
    add_event(session, 'lab-row')
    session.commit()
    with Session(engine, info={'tenant_id': 'other'}) as db:
        add_event(db, 'private-row', sensor='cowrie')
        db.add(Incident(opened_at=T0, last_seen=T0, status='NEW', priority='critical', title='private'))
        db.commit()
    body = report(client)
    assert body['alerts']['count'] == 1
    assert body['honeypots']['event_count'] is None
    assert body['incidents']['items'] == []


@pytest.mark.parametrize('sensors,expected_gpu,expected_temp', [([], None, None), ([
    {'type': 'utilization', 'device_id': 'gpu0', 'reading': {'status': 'ok', 'value': 55, 'unit': 'percent'}},
    {'type': 'temperature', 'device_id': 'gpu0', 'reading': {'status': 'ok', 'value': 45, 'unit': 'celsius'}},
    {'type': 'temperature', 'device_id': 'cpu0', 'reading': {'status': 'unavailable', 'value': 0, 'unit': 'celsius'}},
], 55, 45)])
def test_nullable_sensors_and_selected_range_snapshot(client, session, sensors, expected_gpu, expected_temp):
    agent_id = str(uuid4())
    session.add(CryptoGuardAgent(agent_id=agent_id, host_id='cg-'+agent_id, platform='linux', token_hash='a'*64))
    session.flush()
    for sequence, minutes, cpu in ((1, 5, 71), (2, 70, 22)):
        session.add(CryptoGuardEvent(agent_id=agent_id, event_uid=str(uuid4()), sequence=sequence, event_type='telemetry',
            observed_at=T0 + timedelta(minutes=minutes), payload_sha256=str(sequence)*64, payload={
                'agent_version': 'evaluation', 'snapshot': {'host': {'hostname': 'test-host', 'cpu_percent': {'status':'ok','value':cpu},
                    'memory_used_percent': {'status':'unavailable','value':None}}, 'sensors': sensors}, 'risk': []}))
    session.commit()
    row = report(client)['cryptoguard']['items'][0]
    assert row['cpu_percent'] == 71
    assert row['gpu_percent'] == expected_gpu
    assert row['temperature_c'] == expected_temp
    assert row['ram_percent'] is None
    assert row['resource_impact'] is None


def test_auth_required(client):
    assert client.get('/v1/reports/soc-summary').status_code == 401


def test_invalid_range(client):
    for start, end in ((T0, T0), (T0 + timedelta(days=1), T0), (T0, T0 + timedelta(days=32))):
        assert client.get('/v1/reports/soc-summary', headers=auth('v'), params={
            'from': start.isoformat(), 'to': end.isoformat()}).status_code == 422
    assert client.get('/v1/reports/soc-summary', headers=auth('v'), params={'from': '2026-10-04T00:00:00'}).status_code == 422
