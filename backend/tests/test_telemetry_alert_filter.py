from datetime import timedelta
from app.db.models import Event
from tests.conftest import T0, auth, mk_event


def test_telemetry_does_not_displace_alerts_before_pagination(client, session):
    for i in range(8):
        session.add(Event(**mk_event(f'sample-{i}', sensor='cryptoguard', event_type='telemetry', minutes=i+10).model_dump()))
    for i in range(3):
        session.add(Event(**mk_event(f'alert-{i}', minutes=i, event_type='endpoint_alert').model_dump()))
    session.add(Event(**mk_event('test-alert', execution_mode='TEST', is_test=True).model_dump()))
    session.commit()
    params = {'limit': 2, 'exclude_telemetry': 'true', 'from': T0.isoformat(),
              'to': (T0+timedelta(hours=1)).isoformat()}
    first = client.get('/v1/alerts', params=params, headers=auth('v'))
    assert first.status_code == 200
    body = first.json()
    assert [x['event_uid'] for x in body['items']] == ['alert-2', 'alert-1']
    second = client.get('/v1/alerts', params={**params, 'cursor': body['next_cursor']}, headers=auth('v')).json()
    assert [x['event_uid'] for x in second['items']] == ['alert-0']
    assert second['next_cursor'] is None
    unfiltered = client.get('/v1/alerts', params={'limit': 2}, headers=auth('v')).json()
    assert all(x['event_type'] == 'telemetry' for x in unfiltered['items'])


def test_metrics_excludes_samples_but_preserves_security_detections(client, session):
    for uid, sensor, kind in [('sample', 'cryptoguard', 'telemetry'),
                             ('detection', 'cryptoguard', 'behavioral_alert'),
                             ('wazuh', 'wazuh', 'endpoint_alert')]:
        session.add(Event(**mk_event(uid, sensor=sensor, event_type=kind).model_dump()))
    session.commit()
    filtered = client.get('/v1/metrics', params={'exclude_telemetry': 'true'}, headers=auth('v'))
    assert filtered.status_code == 200
    assert filtered.json()['events_by_source'] == {'cryptoguard': 1, 'wazuh': 1}
    unfiltered = client.get('/v1/metrics', headers=auth('v')).json()
    assert unfiltered['events_by_source'] == {'cryptoguard': 2, 'wazuh': 1}
