import json
import httpx
from fastapi.testclient import TestClient
from app.agent_gateway import app

def test_gateway_scopes_and_limits(tmp_path,monkeypatch):
    config=tmp_path/'gateway.json';config.write_text(json.dumps({'allowed_agent_addresses':['testclient']}))
    monkeypatch.setenv('SENTINELZONE_GATEWAY_CONFIG',str(config))
    with TestClient(app) as client:
        assert client.get('/v1/alerts').status_code==404
        assert client.post('/v1/cryptoguard/agents').status_code==404
        assert client.post('/v1/cryptoguard/enroll').status_code==401
        assert client.post('/v1/cryptoguard/enroll',headers={'Authorization':'Bearer scoped'},content=b'x'*16385).status_code==413
        app.state.allowed=set()
        assert client.post('/v1/cryptoguard/telemetry',headers={'Authorization':'Bearer scoped'}).status_code==403

def test_gateway_forwards_only_agent_auth_and_returns_backend_ack(tmp_path,monkeypatch):
    config=tmp_path/'gateway.json';config.write_text(json.dumps({'allowed_agent_addresses':['testclient']}))
    monkeypatch.setenv('SENTINELZONE_GATEWAY_CONFIG',str(config))
    def handle(request):
        assert request.url.path=='/v1/cryptoguard/telemetry'
        assert request.headers['authorization']=='Bearer scoped'
        assert 'x-forwarded-for' not in request.headers
        return httpx.Response(200,json={'status':'accepted','durable':True})
    with TestClient(app) as client:
        app.state.client=httpx.AsyncClient(base_url='http://127.0.0.1:8003',transport=httpx.MockTransport(handle))
        response=client.post('/v1/cryptoguard/telemetry',headers={'Authorization':'Bearer scoped','X-Forwarded-For':'not-trusted'},json={})
        assert response.status_code==200 and response.json()['durable'] is True
        assert response.headers['cache-control']=='no-store'
