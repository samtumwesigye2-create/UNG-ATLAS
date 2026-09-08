from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse
from pydantic import BaseModel, Field
from datetime import datetime,timezone
import os,json,urllib.request,time
from capability_registry import registry
SYSTEM_ID='UNG-ATLAS';VERSION='0.9.2';app=FastAPI(title='UNG-ATLAS',version=VERSION)
SYSTEMS={'TITAN':('Enterprise Asset Management',['Assets','Work Orders','Maintenance']),'MIDAS':('Finance',['Accounts','Transactions','Approvals']),'NOVA':('Data & Analytics',['Datasets','Analytics','Reports']),'HERMES':('Communications',['Messages','Channels','Delivery']),'NEMSIS':('Emergency Management',['Incidents','Response','Continuity']),'HORUS':('UAS / Aerial Operations',['Aircraft','Missions','Flight Ops']),'ORION':('National Operations Command',['Operations','Situational Awareness','Command']),'MDM':('Master Data Management',['Master Records','Reference Data','Data Quality']),'NEXUS':('Integration & Interoperability',['Interoperability','API Routing','Connectors','Envelope']),'PULSAR':('Data Relay',['Messaging','Delivery','Queue','Retry','DLQ','Fanout'])}
for sid,(name,mods) in SYSTEMS.items():registry.register(sid,name,os.getenv(f'{sid}_BASE_URL',''),mods)
class ServiceIn(BaseModel):system_id:str=Field(min_length=2,max_length=80);name:str=Field(min_length=1,max_length=160);base_url:str='';capabilities:list[str]=Field(default_factory=list);kind:str='internal';active:bool=True
def rec(r):return {'system_id':r.system_id,'name':r.name,'base_url':r.base_url,'capabilities':sorted(r.capabilities),'kind':r.kind,'active':r.active,'updated_at':r.updated_at}
def probe(s,path='/health'):
 r=registry.get(s);u=(r.base_url if r else os.getenv(f'{s}_BASE_URL','')).rstrip('/');t=time.perf_counter()
 if not u:return {'status':'unconfigured','latency_ms':None}
 try:
  with urllib.request.urlopen(u+path,timeout=3) as x:data=json.loads(x.read().decode());status=x.status
  return {'status':'online' if status==200 else 'degraded','latency_ms':round((time.perf_counter()-t)*1000),'data':data}
 except Exception as e:return {'status':'offline','latency_ms':None,'error':type(e).__name__}
def C():return '''*{box-sizing:border-box}body{margin:0;background:#07111f;color:#edf4ff;font-family:system-ui,-apple-system,sans-serif}header{padding:18px;background:#0a1627;border-bottom:1px solid #263d5b}.brand{font-size:21px;font-weight:900}.muted,small{color:#8da3c0}main{max-width:1100px;margin:auto;padding:16px}.panel,.tile{background:#0e1c31;border:1px solid #28415f;border-radius:15px;padding:17px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.tile{text-decoration:none;color:#edf4ff;display:block}.good{color:#65e3a0}.bad{color:#ff7d87}.nav{display:flex;gap:8px;overflow:auto;margin:14px 0}.nav a,.btn{white-space:nowrap;text-decoration:none;color:#dce9fb;background:#101f35;border:1px solid #304b6d;padding:10px 12px;border-radius:10px}.metric{font-size:32px;font-weight:900}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.back{color:#9fc5ff;text-decoration:none}pre{white-space:pre-wrap;background:#081525;border-radius:10px;padding:12px;color:#b9cbe1;max-height:360px;overflow:auto}@media(max-width:700px){.grid,.row{grid-template-columns:1fr}}'''
@app.get('/',response_class=HTMLResponse)
def home():
 cards=''.join(f'<a class="tile" href="/systems/{s}"><small>UNG SYSTEM</small><h2>UNG-{s}</h2><div>{v[0]}</div><p class="good">OPEN WORKSPACE →</p></a>' for s,v in SYSTEMS.items());return f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>{C()}</style></head><body><header><div class="brand">UNG-ATLAS</div><small>Enterprise Control Infrastructure · v{VERSION}</small></header><main><div class="panel"><small>OPERATIONS COMMAND</small><h1>System Workspaces</h1><p class="muted">Open a production system and operate its live interface.</p></div><h3>Production Systems</h3><div class="grid">{cards}</div></main></body></html>'
@app.get('/systems/{sid}',response_class=HTMLResponse)
def workspace(sid:str):
 sid=sid.upper()
 if sid not in SYSTEMS:return RedirectResponse('/')
 name,mods=SYSTEMS[sid];p=probe(sid);cl='good' if p['status']=='online' else 'bad';tabs=''.join(f'<a href="/systems/{sid}/modules/{i}">{m}</a>' for i,m in enumerate(mods));tiles=''.join(f'<a class="tile" href="/systems/{sid}/modules/{i}"><small>MODULE</small><h2>{m}</h2><p class="good">OPEN →</p></a>' for i,m in enumerate(mods))
 return f'''<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>{C()}</style></head><body><header><a class="back" href="/">← ATLAS</a><div class="brand">UNG-{sid}</div><small>{name}</small></header><main><div class="nav"><a href="/systems/{sid}">Overview</a>{tabs}<a href="/systems/{sid}/api">API Console</a></div><div class="row"><div class="panel"><small>RUNTIME</small><div class="metric {cl}">{p['status'].upper()}</div></div><div class="panel"><small>LATENCY</small><div class="metric">{p['latency_ms'] or '—'} ms</div></div><div class="panel"><small>ENVIRONMENT</small><div class="metric">PROD</div></div></div><h3>Modules</h3><div class="grid">{tiles}</div><h3>Live Operations</h3><div class="panel"><button class="btn" onclick="run('/health')">Run Health</button> <button class="btn" onclick="run('/ready')">Run Readiness</button><pre id="out">Select an operation.</pre></div></main><script>async function run(p){{let o=document.getElementById('out');o.textContent='Running...';let r=await fetch('/v1/probe/{sid}?path='+encodeURIComponent(p));o.textContent=JSON.stringify(await r.json(),null,2)}}</script></body></html>'''
@app.get('/systems/{sid}/modules/{idx}',response_class=HTMLResponse)
def module(sid:str,idx:int):
 sid=sid.upper()
 if sid not in SYSTEMS or idx<0 or idx>=len(SYSTEMS[sid][1]):return RedirectResponse(f'/systems/{sid}')
 name,mods=SYSTEMS[sid];m=mods[idx];return f'''<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>{C()}</style></head><body><header><a class="back" href="/systems/{sid}">← UNG-{sid}</a><div class="brand">{m}</div><small>{name}</small></header><main><div class="panel"><small>LIVE MODULE</small><h1>{m}</h1><p class="muted">Production service inspection and API discovery.</p><button class="btn" onclick="load('/v1/system')">Load System Data</button><button class="btn" onclick="load('/health')">Health</button><button class="btn" onclick="load('/ready')">Readiness</button><pre id="out">Tap an action to load live data.</pre></div></main><script>async function load(p){{let o=document.getElementById('out');o.textContent='Loading '+p+'...';let r=await fetch('/v1/proxy/{sid}?path='+encodeURIComponent(p));o.textContent=JSON.stringify(await r.json(),null,2)}}</script></body></html>'''
@app.get('/systems/{sid}/api',response_class=HTMLResponse)
def console(sid:str):return module(sid,0) if sid.upper() in SYSTEMS else RedirectResponse('/')
@app.get('/health')
def health():return {'status':'ok','service':SYSTEM_ID,'version':VERSION,'registry_services':len(registry.list())}
@app.post('/v1/registry/services')
def register_service(p:ServiceIn):return rec(registry.register(p.system_id,p.name,p.base_url,p.capabilities,p.kind,p.active))
@app.get('/v1/registry/services')
def list_services(active_only:bool=False):return {'services':[rec(r) for r in registry.list(active_only)]}
@app.get('/v1/registry/services/{sid}')
def get_service(sid:str):
 r=registry.get(sid)
 if not r:raise HTTPException(404,'service_not_found')
 return rec(r)
@app.get('/v1/registry/discover/{capability}')
def discover(capability:str):return {'capability':capability,'services':[rec(r) for r in registry.discover(capability)]}
@app.get('/v1/probe/{sid}')
def live_probe(sid:str,path:str='/health'):return probe(sid,path if path in ['/health','/ready'] else '/health')
@app.get('/v1/proxy/{sid}')
def proxy(sid:str,path:str='/health'):
 if path not in ['/health','/ready','/v1/system']:return {'error':'endpoint_not_allowed'}
 r=registry.get(sid)
 if not r:return {'error':'system_not_found'}
 return probe(r.system_id,path)
@app.get('/v1/telemetry')
def telemetry():
 x=[dict(id=r.system_id,**probe(r.system_id)) for r in registry.list(active_only=True)];return {'systems':x,'online':sum(v['status']=='online' for v in x),'total':len(x),'timestamp':datetime.now(timezone.utc).isoformat()}
