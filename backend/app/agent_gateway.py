"""TLS ingress limited to agent enrollment/telemetry; the main API stays on loopback."""
import json
import os
from pathlib import Path
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response

@asynccontextmanager
async def lifespan(app):
    config=json.loads(Path(os.environ['SENTINELZONE_GATEWAY_CONFIG']).read_text(encoding='utf-8-sig'))
    app.state.allowed=set(config['allowed_agent_addresses'])
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8003',timeout=20,follow_redirects=False,trust_env=False) as client:
        app.state.client=client
        yield

app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

@app.post('/v1/cryptoguard/{operation}')
async def forward(operation:str,request:Request):
    if operation not in ('enroll','telemetry'):raise HTTPException(404)
    if not request.client or request.client.host not in request.app.state.allowed:raise HTTPException(403)
    authorization=request.headers.get('authorization','')
    if not authorization.startswith('Bearer ') or len(authorization)>512:raise HTTPException(401)
    body=bytearray();limit=16384 if operation=='enroll' else 16*1024*1024
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>limit:raise HTTPException(413)
    try:
        response=await request.app.state.client.post('/v1/cryptoguard/'+operation,content=bytes(body),headers={'Authorization':authorization,'Content-Type':'application/json'})
    except httpx.HTTPError:raise HTTPException(503,'backend unavailable') from None
    return Response(response.content,status_code=response.status_code,media_type='application/json',headers={'Cache-Control':'no-store'})

@app.get('/health')
def health():return {'gateway':'reachable'}
