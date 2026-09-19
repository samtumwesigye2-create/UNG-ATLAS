from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse
from pydantic import BaseModel, Field
from datetime import datetime,timezone
import os,json,urllib.request,time
from capability_registry import registry
SYSTEM_ID='UNG-ATLAS';VERSION='1.1.0';app=FastAPI(title='UNG-ATLAS',version=VERSION)
SYSTEMS={
'ATLAS':('Enterprise Control Infrastructure',['Operations Status','Registry','Dependencies','Tracing']),
'JANUS':('Identity & Access Management',['Identity','MFA','RBAC','Service Identity']),
'NEXUS':('Integration & Interoperability',['Interoperability','API Routing','Connectors','Envelope']),
'LAGRANGE':('Authenticated Service Transport',['Transport','Delivery','Authentication','Reliability']),
'PULSAR':('Data Relay',['Messaging','Delivery','Queue','Retry']),
'VAULT':('Cryptography & Protected Records',['Encryption','Military Vault','Digital SCIF','Receipts']),
'HERMES':('Communications',['Messages','Channels','Delivery']),
'ORION':('National Operations Command',['Operations','Situational Awareness','Command']),
'APOLLO':('Planning & Intelligence',['Planning','Decision Support','Mission Analysis']),
'NOVA':('Data & Analytics',['Datasets','Analytics','Reports']),
'QUASAR':('Correlation & Fusion Analytics',['Correlation','Fusion','Analysis']),
'HEPHA':('Sensor & Operational Fusion',['Sensors','Fusion','Operational Data']),
'DRACO':('Detection, Reconnaissance, Analysis, Collection & Observation',['Collection','Reconnaissance','Surveillance','Detection']),
'CONSTELLATION':('Satellite & Orbital Operations',['Tracking','Orbital Awareness','Space Operations']),
'HORUS':('UAS / Aerial Operations',['Aircraft','Missions','Flight Ops']),
'AEGIS':('Protection & Security',['Protection','Security Operations','Controls']),
'SENTINEL':('Security Operations Center',['Monitoring','Alerts','Incidents','Audit']),
'NEMSIS':('Emergency Management',['Incidents','Response','Continuity']),
'VECTOR':('Warehouse & Logistics',['Inventory','Receiving','Dispatch']),
'MERCURY':('Parcel Processing',['Processing','Sorting','Handoff']),
'UGASHIP':('Shipping & Tracking',['Shipments','Tracking','Delivery']),
'UNG-PROCURE':('Procurement & Demand Intelligence',['Procurement','Demand','Suppliers']),
'TITAN':('Enterprise Asset Management',['Assets','Work Orders','Maintenance']),
'UGAMAP':('Mapping & Routing',['Mapping','Routing','Geospatial']),
'MIDAS':('Finance',['Accounts','Transactions','Approvals']),
'URA-PROMET':('Public Revenue Operations, Management & Electronic Taxation',['Revenue','Tax','Administration']),
'UGAFORCE-HR':('Workforce & Human Resources',['Workforce','Personnel','Administration']),
'PRESIDENT':('Executive Digital Operations',['Executive','Assignments','Service Delivery','Audit']),
'UNG-WAVE':('Wireless Access & Virtualized Edge',['Edge Nodes','Routing','Firewall','VPN']),
'UNG-CAD':('Engineering & CAD Studio',['CAD','Engineering','Manufacturing'])
}
BASE_URL_ALIASES={
'ATLAS':'https://ung-atlas-production.up.railway.app',
'JANUS':'https://ung-iam-production.up.railway.app',
'NEXUS':'https://ung-nexus-production.up.railway.app',
'LAGRANGE':'https://ung-lagrange-production.up.railway.app',
'PULSAR':'https://ung-pulsar-production.up.railway.app',
'VAULT':'https://ung-vault-production.up.railway.app',
'SENTINEL':'https://ung-sentinel-production.up.railway.app',
'DRACO':'https://ung-draco-production-f6b7.up.railway.app'
}
for sid,(name,mods) in SYSTEMS.items():
 base=os.getenv(f'{sid}_BASE_URL','') or BASE_URL_ALIASES.get(sid,'')
 registry.register(sid,name,base,mods)
class ServiceIn(BaseModel):system_id:str=Field(min_length=2,max_length=80);name:str=Field(min_length=1,max_length=160);base_url:str='';capabilities:list[str]=Field(default_factory=list);kind:str='internal';active:bool=True
def rec(r):return {'system_id':r.system_id,'name':r.name,'base_url':r.base_url,'capabilities':sorted(r.capabilities),'kind':r.kind,'active':r.active,'updated_at':r.updated_at}
def probe(s,path='/health'):
 r=registry.get(s);u=(r.base_url if r else (os.getenv(f'{s}_BASE_URL','') or BASE_URL_ALIASES.get(s.replace('UNG-',''),''))).rstrip('/');t=time.perf_counter()
 if not u:return {'status':'unconfigured','latency_ms':None}
 try:
  with urllib.request.urlopen(u+path,timeout=3) as x:data=json.loads(x.read().decode());status=x.status
  return {'status':'online' if status==200 else 'degraded','latency_ms':round((time.perf_counter()-t)*1000),'data':data}
 except Exception as e:return {'status':'offline','latency_ms':None,'error':type(e).__name__}
def C():return '''*{box-sizing:border-box}body{margin:0;background:#07111f;color:#edf4ff;font-family:system-ui,-apple-system,sans-serif}header{padding:18px;background:#0a1627;border-bottom:1px solid #263d5b}.brand{font-size:21px;font-weight:900}.muted,small{color:#8da3c0}main{max-width:1100px;margin:auto;padding:16px}.panel,.tile{background:#0e1c31;border:1px solid #28415f;border-radius:15px;padding:17px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.tile{text-decoration:none;color:#edf4ff;display:block}.good{color:#65e3a0}.bad{color:#ff7d87}.nav{display:flex;gap:8px;overflow:auto;margin:14px 0}.nav a,.btn{white-space:nowrap;text-decoration:none;color:#dce9fb;background:#101f35;border:1px solid #304b6d;padding:10px 12px;border-radius:10px}.metric{font-size:32px;font-weight:900}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.back{color:#9fc5ff;text-decoration:none}pre{white-space:pre-wrap;background:#081525;border-radius:10px;padding:12px;color:#b9cbe1;max-height:360px;overflow:auto}@media(max-width:700px){.grid,.row{grid-template-columns:1fr}}'''
@app.get('/',response_class=HTMLResponse)
def home():
 t=telemetry(); online=t['online']; total=t['total']; degraded=max(total-online,0)
 rows=''.join(f'''<tr><td><b>{x["id"] if x["id"].startswith("UNG-") else "UNG-"+x["id"]}</b></td><td><span class="dot {"on" if x["status"]=="online" else "off"}"></span>{x["status"].upper()}</td><td>{x.get("latency_ms") or "—"} ms</td><td><a href="/systems/{x["id"]}">DETAILS →</a></td></tr>''' for x in t['systems'])
 css=C()+'''body{background:#050b14}.hero{background:linear-gradient(135deg,#0d2038,#0b1628);border:1px solid #294663;border-radius:18px;padding:22px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}.kpi{background:#0d1b2d;border:1px solid #29425e;border-radius:14px;padding:15px}.kpi b{display:block;font-size:27px;margin-top:6px}.ops{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}.ops a{background:#0d1b2d;border:1px solid #29425e;border-radius:13px;padding:15px;color:#dce9fb;text-decoration:none}.ops strong{display:block;margin-bottom:5px}table{width:100%;border-collapse:collapse;background:#0c1829;border:1px solid #29425e;border-radius:14px;overflow:hidden}th,td{text-align:left;padding:12px;border-bottom:1px solid #203650}th{color:#8da3c0;font-size:12px}td a{color:#75e6a7;text-decoration:none}.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:7px}.on{background:#65e3a0}.off{background:#ff7d87}@media(max-width:700px){.kpis{grid-template-columns:1fr 1fr}.ops{grid-template-columns:1fr}table{font-size:13px}th,td{padding:9px}}'''
 return f'''<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css}</style></head><body><header><div class="brand">UNG-ATLAS · NATIONAL OPERATIONS</div><small>Enterprise Control Infrastructure · v{VERSION}</small></header><main><section class="hero"><small>NATIONAL SYSTEMS STATUS</small><h1>Operations Control Board</h1><p class="muted">Live health, control, evidence and certification across the UNG architecture.</p></section><div class="kpis"><div class="kpi"><small>REGISTERED</small><b>{total}</b></div><div class="kpi"><small>ONLINE</small><b class="good">{online}</b></div><div class="kpi"><small>NEEDS ATTENTION</small><b class="bad">{degraded}</b></div><div class="kpi"><small>ENVIRONMENT</small><b>PROD</b></div></div><div class="ops"><a href="/v1/control/status"><strong>CONTROL PLANE</strong>12 operational controls</a><a href="/v1/control/dependencies"><strong>DEPENDENCIES</strong>Architecture dependency graph</a><a href="/v1/control/evidence/verify"><strong>EVIDENCE LEDGER</strong>Tamper-evident verification</a><a href="/v1/control/backups"><strong>DISASTER RECOVERY</strong>Backup and restore status</a><a href="/v1/control/certifications"><strong>CERTIFICATION</strong>Integration acceptance</a><a href="/v1/control/metrics"><strong>OBSERVABILITY</strong>Performance telemetry</a></div><h3>Live Systems</h3><table><thead><tr><th>SYSTEM</th><th>STATUS</th><th>LATENCY</th><th>WORKSPACE</th></tr></thead><tbody>{rows}</tbody></table></main></body></html>'''
@app.get('/systems/{sid}',response_class=HTMLResponse)
def workspace(sid:str):
 sid=sid.upper()
 if sid not in SYSTEMS:return RedirectResponse('/')
 name,mods=SYSTEMS[sid];p=probe(sid);cl='good' if p['status']=='online' else 'bad';tabs=''.join(f'<a href="/systems/{sid}/modules/{i}">{m}</a>' for i,m in enumerate(mods));tiles=''.join(f'<a class="tile" href="/systems/{sid}/modules/{i}"><small>MODULE</small><h2>{m}</h2><p class="good">OPEN →</p></a>' for i,m in enumerate(mods))
 return f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>{C()}</style></head><body><header><a class="back" href="/">← ATLAS</a><div class="brand">UNG-{sid}</div><small>{name}</small></header><main><div class="nav"><a href="/systems/{sid}">Overview</a>{tabs}<a href="/systems/{sid}/api">API Console</a></div><div class="row"><div class="panel"><small>RUNTIME</small><div class="metric {cl}">{p["status"].upper()}</div></div><div class="panel"><small>LATENCY</small><div class="metric">{p["latency_ms"] or "—"} ms</div></div><div class="panel"><small>ENVIRONMENT</small><div class="metric">PROD</div></div></div><h3>Modules</h3><div class="grid">{tiles}</div></main></body></html>'
@app.get('/systems/{sid}/modules/{idx}',response_class=HTMLResponse)
def module(sid:str,idx:int):
 sid=sid.upper()
 if sid not in SYSTEMS or idx<0 or idx>=len(SYSTEMS[sid][1]):return RedirectResponse(f'/systems/{sid}')
 return workspace(sid)
@app.get('/systems/{sid}/api',response_class=HTMLResponse)
def console(sid:str):\n sid=sid.upper().removeprefix('UNG-');return workspace(sid) if sid in SYSTEMS else RedirectResponse('/')
@app.get('/health')
def health():return {'status':'ok','service':SYSTEM_ID,'version':VERSION,'registry_services':len(registry.list())}
@app.get('/v1/system')
def system():return {'system_id':SYSTEM_ID,'version':VERSION,'domain':'enterprise-control-infrastructure','capabilities':['service-registry','capability-discovery','health-probing','edge-node-registry','edge-heartbeats','edge-telemetry','national-operations-status','unified-tracing','tamper-evident-evidence','dependency-registry','disaster-recovery','machine-credential-registry','policy-engine','classification-registry','records-management','observability','integration-certification','cmdb']}
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
@app.get('/v1/telemetry')
def telemetry():
 x=[dict(id=r.system_id,**probe(r.system_id)) for r in registry.list(active_only=True)];return {'systems':x,'online':sum(v['status']=='online' for v in x),'total':len(x),'timestamp':datetime.now(timezone.utc).isoformat()}
from control_plane import router as control_router
from operations_feed import router as operations_router
from edge_nodes import router as edge_router
app.include_router(operations_router);app.include_router(edge_router);app.include_router(control_router)
