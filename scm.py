"""UNG SCM module: standalone ATLAS-mounted operational inventory workspace."""
import os, sqlite3, json, csv, io
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
router=APIRouter(prefix="/scm",tags=["Supply Chain"])
DB=os.getenv("UNG_SCM_DB","/tmp/ung_scm.sqlite3")
def connect():
    db=sqlite3.connect(DB,timeout=10)
    db.row_factory=sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL, name TEXT NOT NULL, quantity REAL NOT NULL DEFAULT 0, unit_cost REAL NOT NULL DEFAULT 0, reorder_point REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active', supplier TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, PRIMARY KEY(kind,id))")
    db.commit()
    return db
KINDS={"inventory","suppliers","purchase_orders","customer_orders","shipments","warehouses"}
class Record(BaseModel):
    id:str=Field(min_length=1,max_length=100)
    name:str=Field(min_length=1,max_length=200)
    quantity:float=Field(default=0,ge=0)
    unit_cost:float=Field(default=0,ge=0)
    reorder_point:float=Field(default=0,ge=0)
    status:str=Field(default="active",max_length=60)
    supplier:str=Field(default="",max_length=200)
def check(kind):
    if kind not in KINDS:raise HTTPException(404,"Unknown resource")
@router.get("/api/{kind}")
def list_records(kind:str):
    check(kind)
    with connect() as db:return [dict(r) for r in db.execute("SELECT * FROM records WHERE kind=? ORDER BY name",(kind,))]
@router.put("/api/{kind}/{id}")
def save(kind:str,id:str,item:Record):
    check(kind)
    if id!=item.id:raise HTTPException(400,"ID mismatch")
    stamp=datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute("INSERT INTO records(kind,id,name,quantity,unit_cost,reorder_point,status,supplier,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET name=excluded.name,quantity=excluded.quantity,unit_cost=excluded.unit_cost,reorder_point=excluded.reorder_point,status=excluded.status,supplier=excluded.supplier,updated_at=excluded.updated_at",(kind,id,item.name,item.quantity,item.unit_cost,item.reorder_point,item.status,item.supplier,stamp))
    return {"saved":True,"id":id}
@router.delete("/api/{kind}/{id}")
def remove(kind:str,id:str):
    check(kind)
    with connect() as db:db.execute("DELETE FROM records WHERE kind=? AND id=?",(kind,id))
    return {"deleted":True}
@router.get("/api/summary")
def summary():
    with connect() as db:
        inv=[dict(x) for x in db.execute("SELECT * FROM records WHERE kind='inventory'")]
        totals={k:db.execute("SELECT COUNT(*) FROM records WHERE kind=?",(k,)).fetchone()[0] for k in KINDS}
    return {"counts":totals,"inventory_value":round(sum(x["quantity"]*x["unit_cost"] for x in inv),2),"low_stock":[x for x in inv if x["quantity"]<=x["reorder_point"]]}
@router.get("/api/export/{kind}")
def export(kind:str):
    check(kind)
    rows=list_records(kind)
    f=io.StringIO();writer=csv.DictWriter(f,fieldnames=["kind","id","name","quantity","unit_cost","reorder_point","status","supplier","updated_at"]);writer.writeheader();writer.writerows(rows)
    return StreamingResponse(iter([f.getvalue()]),media_type="text/csv",headers={"Content-Disposition":f"attachment; filename=ung-{kind}.csv"})
@router.get("",response_class=HTMLResponse)
def page():
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNG Supply Chain</title>
<style>body{margin:0;background:#081525;color:#eaf2ff;font:15px system-ui}header{padding:20px 28px;background:#0d2444}h1{margin:0;font-size:25px}main{max-width:1200px;margin:auto;padding:20px}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}button,a{background:#164a86;color:white;border:1px solid #356ba1;border-radius:8px;padding:10px;cursor:pointer;text-decoration:none}.active{background:#137d94}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.card,section{background:#10243c;border:1px solid #274460;border-radius:12px;padding:16px;margin-bottom:15px}.num{font-size:26px;font-weight:bold;color:#78dce7}input{background:#091b2d;color:white;border:1px solid #48617b;padding:10px;border-radius:7px;max-width:160px}form{display:flex;gap:8px;flex-wrap:wrap}table{width:100%;border-collapse:collapse;min-width:700px}td,th{padding:11px;border-bottom:1px solid #30465b;text-align:left}.scroll{overflow:auto}.danger{color:#ff9c9c}small{color:#a4b8d0}</style>
<header><h1>UNG · Supply Chain Command Center</h1><small>ATLAS / VECTOR / Procurement / Logistics</small></header><main><div class="cards" id="stats"></div><nav class="tabs" id="tabs"></nav><section><h2 id="heading">Inventory</h2><form id="editor"><input name="id" placeholder="Record ID" required><input name="name" placeholder="Name" required><input name="quantity" type="number" min="0" step="any" placeholder="Quantity"><input name="unit_cost" type="number" min="0" step="any" placeholder="Unit cost"><input name="reorder_point" type="number" min="0" step="any" placeholder="Reorder point"><input name="supplier" placeholder="Supplier"><input name="status" placeholder="Status"><button>Save record</button></form><p><a id="export">Export CSV</a></p><div class="scroll"><table><thead><tr><th>ID</th><th>Name</th><th>Quantity</th><th>Unit cost</th><th>Status</th><th>Supplier</th><th>Actions</th></tr></thead><tbody id="records"></tbody></table></div></section><section><h2>Stock risk</h2><div id="risks"></div></section><small>Operational data is stored in the configured SQLite database. Production deployment requires persistent storage and access control.</small></main>
<script>
const kinds=['inventory','suppliers','purchase_orders','customer_orders','shipments','warehouses'];let kind='inventory';let rows=[];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function request(url,options){const r=await fetch(url,options);if(!r.ok)throw Error(await r.text());return r.json()}
async function refresh(){const [sum,data]=await Promise.all([request('/scm/api/summary'),request('/scm/api/'+kind)]);rows=data;document.getElementById('stats').innerHTML='<div class="card">Inventory value<div class="num">$'+sum.inventory_value.toLocaleString()+'</div></div><div class="card">Low stock<div class="num">'+sum.low_stock.length+'</div></div>'+Object.entries(sum.counts).map(([k,v])=>'<div class="card">'+esc(k.replaceAll('_',' '))+'<div class="num">'+v+'</div></div>').join('');document.getElementById('risks').innerHTML=sum.low_stock.map(x=>'<p class="danger">'+esc(x.id)+' · '+esc(x.name)+' · '+x.quantity+' remaining</p>').join('')||'No low-stock records';document.getElementById('records').innerHTML=rows.map((x,i)=>'<tr><td>'+esc(x.id)+'</td><td>'+esc(x.name)+'</td><td>'+x.quantity+'</td><td>'+x.unit_cost+'</td><td>'+esc(x.status)+'</td><td>'+esc(x.supplier)+'</td><td><button onclick="edit('+i+')">Edit</button> <button onclick="del('+i+')">Delete</button></td></tr>').join('');document.getElementById('export').href='/scm/api/export/'+kind}
function select(k){kind=k;document.getElementById('heading').textContent=k.replaceAll('_',' ');document.getElementById('tabs').innerHTML=kinds.map(x=>'<button class="'+(x===kind?'active':'')+'" onclick="select(\''+x+'\')">'+x.replaceAll('_',' ')+'</button>').join('');document.getElementById('editor').reset();refresh().catch(alert)}
function edit(i){const f=document.getElementById('editor');for(const [k,v] of Object.entries(rows[i]))if(f.elements[k])f.elements[k].value=v;window.scrollTo({top:150,behavior:'smooth'})}
async function del(i){if(!confirm('Delete this record?'))return;await request('/scm/api/'+kind+'/'+encodeURIComponent(rows[i].id),{method:'DELETE'});refresh()}
document.getElementById('editor').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));for(const k of ['quantity','unit_cost','reorder_point'])d[k]=Number(d[k]||0);try{await request('/scm/api/'+kind+'/'+encodeURIComponent(d.id),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});e.target.reset();refresh()}catch(e){alert(e.message)}};select('inventory');
</script></html>"""
