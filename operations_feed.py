import csv, io, json, os, urllib.error, urllib.parse, urllib.request
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/v1/operations", tags=["Operational Activity"])
SENTINEL_BASE_URL = os.getenv('SENTINEL_BASE_URL','https://ung-sentinel-production.up.railway.app').rstrip('/')

def fetch_sentinel(path: str, authorization: str | None):
    if not authorization:
        raise HTTPException(401,'JANUS bearer token required')
    req=urllib.request.Request(SENTINEL_BASE_URL+path,headers={'Authorization':authorization,'User-Agent':'UNG-ATLAS/0.9.4'})
    try:
        with urllib.request.urlopen(req,timeout=8) as r:
            return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        if e.code in (401,403): raise HTTPException(e.code,'SENTINEL authorization rejected')
        raise HTTPException(502,f'SENTINEL http_{e.code}')
    except Exception as e:
        raise HTTPException(503,f'SENTINEL unavailable:{type(e).__name__}')

def _event_path(source_system=None,module=None,entity_type=None,entity_id=None,limit=1000):
    params={'limit':max(1,min(limit,1000))}
    if source_system: params['source_system']=source_system
    if module: params['module']=module
    if entity_type: params['entity_type']=entity_type
    if entity_id: params['entity_id']=entity_id
    return '/v1/operations/events?'+urllib.parse.urlencode(params)

@router.get('/feed')
def activity_feed(source_system: str | None = None, module: str | None = None, entity_type: str | None = None, entity_id: str | None = None, limit: int = 200, authorization: str | None = Header(None)):
    return fetch_sentinel(_event_path(source_system,module,entity_type,entity_id,limit),authorization)

@router.get('/summary')
def activity_summary(authorization: str | None = Header(None)):
    return fetch_sentinel('/v1/operations/summary',authorization)

@router.get('/timeline/{entity_type}/{entity_id}')
def entity_timeline(entity_type: str, entity_id: str, authorization: str | None = Header(None)):
    path='/v1/operations/timeline/'+urllib.parse.quote(entity_type,safe='')+'/'+urllib.parse.quote(entity_id,safe='')
    return fetch_sentinel(path,authorization)

@router.get('/reports/activity')
def activity_report(source_system: str | None = None, module: str | None = None, entity_type: str | None = None, entity_id: str | None = None, limit: int = 1000, authorization: str | None = Header(None)):
    rows=fetch_sentinel(_event_path(source_system,module,entity_type,entity_id,limit),authorization)
    if not isinstance(rows,list): rows=[]
    by_system={}; by_module={}; by_status={}
    for r in rows:
        by_system[r.get('source_system') or 'unknown']=by_system.get(r.get('source_system') or 'unknown',0)+1
        by_module[r.get('module') or 'unknown']=by_module.get(r.get('module') or 'unknown',0)+1
        by_status[r.get('status') or 'unspecified']=by_status.get(r.get('status') or 'unspecified',0)+1
    return {'report':'operational-activity','events':len(rows),'by_system':by_system,'by_module':by_module,'by_status':by_status,'filters':{'source_system':source_system,'module':module,'entity_type':entity_type,'entity_id':entity_id}}

@router.get('/reports/activity.csv')
def activity_csv(source_system: str | None = None, module: str | None = None, entity_type: str | None = None, entity_id: str | None = None, limit: int = 1000, authorization: str | None = Header(None)):
    rows=fetch_sentinel(_event_path(source_system,module,entity_type,entity_id,limit),authorization)
    if not isinstance(rows,list): rows=[]
    fields=['id','source_system','module','entity_type','entity_id','action','actor_id','status','occurred_at','created_at','details']
    out=io.StringIO(); writer=csv.writer(out); writer.writerow(fields)
    for r in rows:
        writer.writerow([json.dumps(r.get(k),separators=(',',':')) if k=='details' else r.get(k) for k in fields])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="ung-atlas-operational-activity.csv"'})
