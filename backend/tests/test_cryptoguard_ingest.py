import copy,json,secrets
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.cryptoguard.models import CryptoGuardEvent,CryptoGuardAgent
from app.db.models import Event,Incident
from tests.conftest import auth

def enroll(client,platform='linux',agent_id=None):
    aid=agent_id or str(uuid4())
    ticket=client.post('/v1/cryptoguard/enrollment-tokens',headers=auth('ad'),json={'agent_id':aid,'platform':platform})
    assert ticket.status_code==201
    body={'agent_id':aid,'platform':platform}
    response=client.post('/v1/cryptoguard/enroll',headers={'Authorization':'Bearer '+ticket.json()['enrollment_token']},json=body)
    assert response.status_code==201
    return aid,{'Authorization':'Bearer '+response.json()['agent_token']},ticket.json()['enrollment_token']

def sample(aid,platform='linux'):
    p=json.loads((Path(__file__).parent/'fixtures/cryptoguard-telemetry.json').read_text(encoding='utf-8-sig'))
    p.update(agent_id=aid,event_uid=str(uuid4()),observed_at=datetime.now(timezone.utc).isoformat(),sequence=1)
    p['snapshot']['host']['platform']=platform
    return p

@pytest.mark.parametrize('platform',['windows','linux'])
def test_durable_roundtrip_dedup_null_and_independent_risk(client,session,platform):
    aid,headers,_=enroll(client,platform)
    p=sample(aid,platform)
    first=client.post('/v1/cryptoguard/telemetry',headers=headers,json=p)
    assert first.status_code==200 and first.json()['durable'] is True
    assert first.json()['event_uid']==p['event_uid']
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=p).json()['status']=='duplicate'
    assert session.scalar(select(func.count()).select_from(CryptoGuardEvent))==1
    assert session.scalar(select(func.count()).select_from(Event))==1
    assert session.scalar(select(func.count()).select_from(Incident))==0
    out=client.get('/v1/cryptoguard/agents/'+aid,headers=auth('v')).json()
    assert out['status']=='online' and out['host_id']=='cg-'+aid
    assert out['snapshot']['host']['idle_seconds']['value'] is None
    assert out['snapshot']['host']['cpu_percent']['value']==99
    assert out['security_risk']==0
    assert out['resource_impact'] is None

def test_uid_payload_and_sequence_collisions(client,session):
    aid,headers,_=enroll(client);p=sample(aid)
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=p).status_code==200
    p['snapshot']['host']['hostname']='changed'
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=p).status_code==409
    p['event_uid']=str(uuid4())
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=p).status_code==409
    assert session.scalar(select(func.count()).select_from(CryptoGuardEvent))==1

def test_credential_scope_replay_and_revocation(client):
    aid,headers,ticket=enroll(client);p=sample(aid)
    assert client.post('/v1/cryptoguard/enroll',headers={'Authorization':'Bearer '+ticket},json={'agent_id':aid,'platform':'linux'}).status_code==401
    assert client.get('/v1/alerts',headers=headers).status_code==401
    assert client.post('/v1/cryptoguard/telemetry',headers=auth('ad'),json=p).status_code==401
    assert client.post('/v1/cryptoguard/enrollment-tokens',headers=auth('v'),json={'agent_id':str(uuid4()),'platform':'linux'}).status_code==403
    p['agent_id']=str(uuid4())
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=p).status_code==403
    assert client.post('/v1/cryptoguard/agents/'+aid+'/revoke',headers=auth('ad')).status_code==204
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=sample(aid)).status_code==401

@pytest.mark.parametrize('field,value',[('schema_version','0'),('event_uid','bad'),('sequence',0),('observed_at','yesterday'),('extra','secret-value')])
def test_contract_validation_sanitized(client,field,value):
    aid,headers,_=enroll(client);p=sample(aid);p[field]=value
    r=client.post('/v1/cryptoguard/telemetry',headers=headers,json=p)
    assert r.status_code==422
    assert 'secret-value' not in r.text

def test_host_rename_preserves_identity_and_old_events_do_not_regress_last_seen(client):
    aid,headers,_=enroll(client);p=sample(aid)
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=p).status_code==200
    p.update(sequence=2,event_uid=str(uuid4()),observed_at='2020-01-01T00:00:00Z')
    p['snapshot']['host']['hostname']='renamed'
    assert client.post('/v1/cryptoguard/telemetry',headers=headers,json=p).status_code==200
    out=client.get('/v1/cryptoguard/agents/'+aid,headers=auth('v')).json()
    assert out['status']=='online' and out['host_id']=='cg-'+aid
    assert out['snapshot']['host']['hostname']!='renamed'

def test_wazuh_json_source_allowlist():
    from app.connectors.splunk import SplunkConnector
    row={'index':'wazuh','source':'/var/ossec/logs/alerts/alerts.json','sourcetype':'_json','_raw':'{"id":"1"}'}
    assert SplunkConnector._to_raw(row).kind=='wazuh'
    row['source']='unrelated'
    assert SplunkConnector._to_raw(row) is None

def test_syslog_and_truncated_events_are_isolated():
    from app.connectors.splunk import SplunkConnector
    row={'index':'suricata','sourcetype':'suricata:eve','_raw':'Oct  6 17:26:49 10.10.100.1 Oct  6 17:26:49 suricata[66043]: {"timestamp":"2026-10-06T13:26:49Z"}'}
    assert SplunkConnector._to_raw(row).payload['timestamp']=='2026-10-06T13:26:49Z'
    row['_raw']=row['_raw'][:-1]
    assert SplunkConnector._to_raw(row).payload=={}
