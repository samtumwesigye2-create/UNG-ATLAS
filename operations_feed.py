import json, os, urllib.error, urllib.parse, urllib.request
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/v1/operations", tags=["Operational Activity"])
SENTINEL_BASE_URL = os.getenv('SENTINEL_BASE_URL','https://ung-sentinel-production.up.railway.app').rstrip('/')

def fetch_sentinel(path: str, authorization: str | None):
    if not authorization:
        raise HTTPException(401,'JANUS bearer token required')
    req=urllib.request.Request(SENTINEL_BASE_URL+path,headers={'Authorization':authorization,'User-Agent':'UNG-ATLAS/0.9.3'})
    try:
        with urllib.request.urlopen(req,timeout=8) as r:
            return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        if e.code in (401,403): raise HTTPException(e.code,'SENTINEL authorization rejected')
        raise HTTPException(502,f'SENTINEL http_{e.code}')
    except Exception as e:
        raise HTTPException(503,f'SENTINEL unavailable:{type(e).__name__}')

@router.get('/feed')
def activity_feed(source_system: str | None = None, module: str | None = None, entity_type: str | None = None, entity_id: str | None = None, limit: int = 200, authorization: str | None = Header(None)):
    params={'limit':max(1,min(limit,1000))}
    if source_system: params['source_system']=source_system
    if module: params['module']=module
    if entity_type: params['entity_type']=entity_type
    if entity_id: params['entity_id']=entity_id
    return fetch_sentinel('/v1/operations/events?'+urllib.parse.urlencode(params),authorization)

@router.get('/summary')
def activity_summary(authorization: str | None = Header(None)):
    return fetch_sentinel('/v1/operations/summary',authorization)

@router.get('/timeline/{entity_type}/{entity_id}')
def entity_timeline(entity_type: str, entity_id: str, authorization: str | None = Header(None)):
    path='/v1/operations/timeline/'+urllib.parse.quote(entity_type,safe='')+'/'+urllib.parse.quote(entity_id,safe='')
    return fetch_sentinel(path,authorization)
