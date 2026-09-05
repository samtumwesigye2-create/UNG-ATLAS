from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timezone
import os,json,urllib.request,time
SYSTEM_ID='UNG-ATLAS';VERSION='0.5.0'
app=FastAPI(title='UNG-ATLAS',version=VERSION)
SYSTEMS={'TITAN':('Enterprise Asset Management','Assets','Work Orders','Maintenance'), 'MIDAS':('Finance','Accounts','Transactions','Approvals'), 'NOVA':('Data & Analytics','Datasets','Analytics','Reports'), 'HERMES':('Communications','Messages','Channels','Delivery'), 'NEMSIS':('Emergency Management','Incidents','Response','Continuity'), 'HORUS':('UAS / Aerial Operations','Aircraft','Missions','Flight Ops')}
def probe(s,path='/health'):
 u=os.getenv(f'{s}_BASE_URL','').rstrip('/');t=time.perf_counter()
 if not u:return {'status':'unconfigured','latency_ms':None}
 try:
  with urllib.request.urlopen(u+path,timeout=3) as r:data=json.loads(r.read().decode())
  return {'status':'online' if r.status==200 else 'degraded','latency_ms':round((time.perf_counter()-t)*1000),'data':data}
 except Exception as e:return {'status':'offline','latency_ms':None,'error':type(e).__name__}
def css():return '''*{box-sizing:border-box}body{margin:0;background:#07111f;color:#edf4ff;font-family:system-ui,-apple-system,sans-serif}header{padding:18px;background:#0a1627;border-bottom:1px solid #263d5b}.brand{font-size:21px;font-weight:900}.muted,small{color:#8da3c0}main{max-width:1100px;margin:auto;padding:16px}.panel,.tile{background:#0e1c31;border:1px solid #28415f;border-radius:15px;padding:17px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.tile{text-decoration:none;color:#edf4ff;display:block}.tile h3{margin:9px 0}.good{color:#65e3a0}.bad{color:#ff7d87}.nav{display:flex;gap:8px;overflow:auto;margin:14px 0}.nav a,.btn{white-space:nowrap;text-decoration:none;color:#dce9fb;background:#101f35;border:1px solid #304b6d;padding:10px 12px;border-radius:10px}.metric{font-size:34px;font-weight:900}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.back{color:#9fc5ff;text-decoration:none}pre{white-space:pre-wrap;background:#081525;border-radius:10px;padding:12px;color:#b9cbe1;max-height:260px;overflow:auto}@media(max-width:700px){.grid,.row{grid-template-columns:1fr}}'''
@app.get('/',response_class=HTMLResponse)
def home():
 cards=''.join(f'''<a class="tile" href="/systems/{s}"><small>UNG SYSTEM</small><h3>UNG-{s}</h3><div>{v[0]}</div><p class="good">OPEN WORKSPACE →</p></a>''' for s,v in SYSTEMS.items())
 return f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css()}</style></head><body><header><div class="brand">UNG-ATLAS</div><small>Enterprise Control Infrastructure · v{VERSION}</small></header><main><div class="panel"><small>OPERATIONS COMMAND</small><h1>System Workspaces</h1><p class="muted">Open a system to inspect its live runtime, readiness and operational API.</p></div><h3>Production Systems</h3><div class="grid">{cards}</div></main></body></html>'''
@app.get('/systems/{sid}',response_class=HTMLResponse)
def workspace(sid:str):
 sid=sid.upper()
 if sid not in SYSTEMS:return RedirectResponse('/')
 name,*modules=SYSTEMS[sid];p=probe(sid);cl='good' if p['status']=='online' else 'bad';base=os.getenv(f'{sid}_BASE_URL','')
 tabs=''.join(f'<a href="#">{m}</a>' for m in modules)
 return f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNG-{sid}</title><style>{css()}</style></head><body><header><a class="back" href="/">← ATLAS</a><div class="brand">UNG-{sid}</div><small>{name}</small></header><main><div class="nav"><a href="/systems/{sid}">Overview</a>{tabs}<a href="/systems/{sid}/api">API Console</a></div><div class="row"><div class="panel"><small>RUNTIME</small><div class="metric {cl}">{p['status'].upper()}</div></div><div class="panel"><small>LATENCY</small><div class="metric">{p['latency_ms'] if p['latency_ms'] is not None else '—'} ms</div></div><div class="panel"><small>ENVIRONMENT</small><div class="metric">PROD</div></div></div><h3>Operations</h3><div class="panel"><button class="btn" onclick="run('/health')">Run Health</button> <button class="btn" onclick="run('/ready')">Run Readiness</button> <button class="btn" onclick="location.href='/systems/{sid}/api'">Open API Console</button><pre id="out">Select an operation.</pre></div><h3>Service Endpoint</h3><div class="panel"><small>{base}</small></div></main><script>async function run(p){{let o=document.getElementById('out');o.textContent='Running '+p+'...';let r=await fetch('/v1/probe/{sid}?path='+p);o.textContent=JSON.stringify(await r.json(),null,2)}}</script></body></html>'''
@app.get('/systems/{sid}/api',response_class=HTMLResponse)
def console(sid:str):
 sid=sid.upper()
 if sid not in SYSTEMS:return RedirectResponse('/')
 return f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css()}</style></head><body><header><a class="back" href="/systems/{sid}">← UNG-{sid}</a><div class="brand">Operational API Console</div></header><main><div class="panel"><h2>UNG-{sid}</h2><p class="muted">Execute approved read-only production endpoints.</p><div class="nav"><button class="btn" onclick="go('/health')">/health</button><button class="btn" onclick="go('/ready')">/ready</button><button class="btn" onclick="go('/v1/system')">/v1/system</button></div><pre id="out">Choose an endpoint.</pre></div></main><script>async function go(p){{let o=document.getElementById('out');o.textContent='Requesting '+p+'...';let r=await fetch('/v1/proxy/{sid}?path='+encodeURIComponent(p));o.textContent=JSON.stringify(await r.json(),null,2)}}</script></body></html>'''
@app.get('/health')
def health():return {'status':'ok','service':SYSTEM_ID,'version':VERSION}
@app.get('/v1/probe/{sid}')
def live_probe(sid:str,path:str='/health'):
 sid=sid.upper();return probe(sid,path if path in ['/health','/ready'] else '/health') if sid in SYSTEMS else {'status':'unknown'}
@app.get('/v1/proxy/{sid}')
def proxy(sid:str,path:str='/health'):
 sid=sid.upper()
 if sid not in SYSTEMS or path not in ['/health','/ready','/v1/system']:return {'error':'endpoint_not_allowed'}
 return probe(sid,path)
@app.get('/v1/telemetry')
def telemetry():
 x=[dict(id='UNG-'+s,**probe(s)) for s in SYSTEMS];return {'systems':x,'online':sum(v['status']=='online' for v in x),'total':len(x),'timestamp':datetime.now(timezone.utc).isoformat()}
