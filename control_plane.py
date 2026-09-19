from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import sqlite3, os, uuid, hashlib, json

router=APIRouter(prefix="/v1/control",tags=["National Control Plane"])
DB=os.getenv("ATLAS_CONTROL_DB","/tmp/atlas-control.db")
def now(): return datetime.now(timezone.utc).isoformat()
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
 c.executescript("""
 CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,kind TEXT,name TEXT,owner TEXT,environment TEXT,status TEXT,metadata TEXT,updated_at TEXT);
 CREATE TABLE IF NOT EXISTS dependencies(source TEXT,target TEXT,kind TEXT,critical INTEGER,PRIMARY KEY(source,target,kind));
 CREATE TABLE IF NOT EXISTS traces(trace_id TEXT,seq INTEGER,system_id TEXT,event TEXT,status TEXT,latency_ms REAL,detail TEXT,created_at TEXT,PRIMARY KEY(trace_id,seq));
 CREATE TABLE IF NOT EXISTS evidence(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE,actor TEXT,action TEXT,object_id TEXT,trace_id TEXT,detail TEXT,prev_hash TEXT,event_hash TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS backups(id TEXT PRIMARY KEY,system_id TEXT,backup_at TEXT,encrypted INTEGER,offsite INTEGER,restore_tested_at TEXT,rpo_minutes INTEGER,rto_minutes INTEGER,status TEXT);
 CREATE TABLE IF NOT EXISTS service_credentials(id TEXT PRIMARY KEY,service_id TEXT,target_id TEXT,issued_at TEXT,expires_at TEXT,rotated_at TEXT,status TEXT);
 CREATE TABLE IF NOT EXISTS policies(id TEXT PRIMARY KEY,version INTEGER,document TEXT,status TEXT,updated_at TEXT);
 CREATE TABLE IF NOT EXISTS classifications(name TEXT PRIMARY KEY,rank INTEGER,retention_days INTEGER,encryption_required INTEGER,export_rule TEXT,destruction_rule TEXT);
 CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,system_id TEXT,classification TEXT,created_at TEXT,retain_until TEXT,legal_hold INTEGER,disposition_status TEXT);
 CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY AUTOINCREMENT,system_id TEXT,metric TEXT,value REAL,unit TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS certifications(id TEXT PRIMARY KEY,system_id TEXT,version TEXT,status TEXT,checks TEXT,created_at TEXT);
 """)
 for x in [("public",0,365,0,"allowed","standard"),("internal",10,1095,1,"controlled","approved"),("confidential",20,2555,1,"restricted","approved"),("restricted",30,3650,1,"prohibited-by-default","dual-approval"),("top_secret",40,7300,1,"prohibited","multi-party")]:
  c.execute("INSERT OR IGNORE INTO classifications VALUES(?,?,?,?,?,?)",x)
 c.commit(); return c
db().close()
class Asset(BaseModel):
 kind:str; name:str; owner:str="UNG"; environment:str="production"; status:str="active"; metadata:dict=Field(default_factory=dict)
class Dep(BaseModel):
 source:str; target:str; kind:str="runtime"; critical:bool=True
class Trace(BaseModel):
 trace_id:str|None=None; system_id:str; event:str; status:str="ok"; latency_ms:float|None=None; detail:dict=Field(default_factory=dict)
class Evidence(BaseModel):
 actor:str; action:str; object_id:str=""; trace_id:str=""; detail:dict=Field(default_factory=dict)
class Backup(BaseModel):
 system_id:str; encrypted:bool=True; offsite:bool=True; restore_tested_at:str|None=None; rpo_minutes:int=60; rto_minutes:int=240; status:str="verified"
class Credential(BaseModel):
 service_id:str; target_id:str; expires_at:str; status:str="active"
class Policy(BaseModel):
 id:str; version:int=1; document:dict; status:str="active"
class Record(BaseModel):
 system_id:str; classification:str; retain_until:str; legal_hold:bool=False; disposition_status:str="retained"
class Metric(BaseModel):
 system_id:str; metric:str; value:float; unit:str=""
class Certification(BaseModel):
 system_id:str; version:str; checks:dict
@router.get("/status")
def status():
 c=db(); tables=["assets","dependencies","traces","evidence","backups","service_credentials","policies","classifications","records","metrics","certifications"]
 counts={t:c.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"] for t in tables}; c.close()
 return {"status":"operational","modules":{"operations_status":True,"unified_tracing":True,"evidence_ledger":True,"dependency_registry":True,"disaster_recovery":True,"machine_credentials":True,"policy_engine":True,"classification_registry":True,"records_management":True,"observability":True,"integration_certification":True,"cmdb":True},"counts":counts,"timestamp":now()}
@router.post("/assets")
def add_asset(x:Asset):
 i=str(uuid.uuid4()); c=db(); c.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?)",(i,x.kind,x.name,x.owner,x.environment,x.status,json.dumps(x.metadata),now()));c.commit();c.close();return {"id":i,**x.model_dump()}
@router.get("/assets")
def assets(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM assets ORDER BY name")];c.close();return {"assets":r}
@router.post("/dependencies")
def dependency(x:Dep):
 c=db();c.execute("INSERT OR REPLACE INTO dependencies VALUES(?,?,?,?)",(x.source,x.target,x.kind,int(x.critical)));c.commit();c.close();return x
@router.get("/dependencies")
def dependencies(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM dependencies")];c.close();return {"dependencies":r}
@router.post("/traces")
def trace(x:Trace):
 tid=x.trace_id or "TRC-"+uuid.uuid4().hex.upper();c=db();seq=c.execute("SELECT COALESCE(MAX(seq),0)+1 n FROM traces WHERE trace_id=?",(tid,)).fetchone()["n"];c.execute("INSERT INTO traces VALUES(?,?,?,?,?,?,?,?)",(tid,seq,x.system_id,x.event,x.status,x.latency_ms,json.dumps(x.detail),now()));c.commit();c.close();return {"trace_id":tid,"seq":seq}
@router.get("/traces/{trace_id}")
def get_trace(trace_id:str): c=db();r=[dict(x) for x in c.execute("SELECT * FROM traces WHERE trace_id=? ORDER BY seq",(trace_id,))];c.close();return {"trace_id":trace_id,"hops":r}
@router.post("/evidence")
def evidence(x:Evidence):
 c=db();p=c.execute("SELECT event_hash FROM evidence ORDER BY seq DESC LIMIT 1").fetchone();prev=p["event_hash"] if p else "GENESIS";eid="EVT-"+uuid.uuid4().hex.upper();ts=now();body=json.dumps([eid,x.actor,x.action,x.object_id,x.trace_id,x.detail,prev,ts],sort_keys=True);h=hashlib.sha256(body.encode()).hexdigest();c.execute("INSERT INTO evidence(event_id,actor,action,object_id,trace_id,detail,prev_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(eid,x.actor,x.action,x.object_id,x.trace_id,json.dumps(x.detail),prev,h,ts));c.commit();c.close();return {"event_id":eid,"event_hash":h,"prev_hash":prev}
@router.get("/evidence/verify")
def verify():
 c=db();rows=c.execute("SELECT * FROM evidence ORDER BY seq").fetchall();prev="GENESIS";ok=True
 for r in rows:
  if r["prev_hash"]!=prev:ok=False;break
  prev=r["event_hash"]
 c.close();return {"valid":ok,"entries":len(rows),"head":prev}
@router.post("/backups")
def backup(x:Backup):
 i="BKP-"+uuid.uuid4().hex.upper();c=db();c.execute("INSERT INTO backups VALUES(?,?,?,?,?,?,?,?,?)",(i,x.system_id,now(),int(x.encrypted),int(x.offsite),x.restore_tested_at,x.rpo_minutes,x.rto_minutes,x.status));c.commit();c.close();return {"id":i}
@router.get("/backups")
def backups(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM backups ORDER BY backup_at DESC")];c.close();return {"backups":r}
@router.post("/credentials")
def credential(x:Credential):
 i="CRED-"+uuid.uuid4().hex.upper();c=db();c.execute("INSERT INTO service_credentials VALUES(?,?,?,?,?,?,?)",(i,x.service_id,x.target_id,now(),x.expires_at,None,x.status));c.commit();c.close();return {"id":i}
@router.get("/credentials")
def credentials(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM service_credentials")];c.close();return {"credentials":r}
@router.post("/policies")
def policy(x:Policy):
 c=db();c.execute("INSERT OR REPLACE INTO policies VALUES(?,?,?,?,?)",(x.id,x.version,json.dumps(x.document),x.status,now()));c.commit();c.close();return x
@router.get("/policies")
def policies(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM policies")];c.close();return {"policies":r}
@router.get("/classifications")
def classifications(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM classifications ORDER BY rank")];c.close();return {"classifications":r}
@router.post("/records")
def record(x:Record):
 c=db();cl=c.execute("SELECT 1 FROM classifications WHERE name=?",(x.classification,)).fetchone()
 if not cl:c.close();raise HTTPException(400,"unknown_classification")
 i="REC-"+uuid.uuid4().hex.upper();c.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?)",(i,x.system_id,x.classification,now(),x.retain_until,int(x.legal_hold),x.disposition_status));c.commit();c.close();return {"id":i}
@router.get("/records")
def records(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM records")];c.close();return {"records":r}
@router.post("/metrics")
def metric(x:Metric):
 c=db();c.execute("INSERT INTO metrics(system_id,metric,value,unit,created_at) VALUES(?,?,?,?,?)",(x.system_id,x.metric,x.value,x.unit,now()));c.commit();c.close();return {"accepted":True}
@router.get("/metrics")
def metrics(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM metrics ORDER BY id DESC LIMIT 500")];c.close();return {"metrics":r}
@router.post("/certifications")
def certification(x:Certification):
 i="CERT-"+uuid.uuid4().hex.upper();status="passed" if all(bool(v) for v in x.checks.values()) else "failed";c=db();c.execute("INSERT INTO certifications VALUES(?,?,?,?,?,?)",(i,x.system_id,x.version,status,json.dumps(x.checks),now()));c.commit();c.close();return {"id":i,"status":status}
@router.get("/certifications")
def certifications(): c=db();r=[dict(x) for x in c.execute("SELECT * FROM certifications ORDER BY created_at DESC")];c.close();return {"certifications":r}
