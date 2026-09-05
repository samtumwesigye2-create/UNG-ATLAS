from fastapi import FastAPI
from fastapi.responses import HTMLResponse

SYSTEM_ID = "UNG-ATLAS"
VERSION = "0.2.0"

app = FastAPI(title="UNG-ATLAS Control Infrastructure", version=VERSION)

SYSTEMS = [
    ("TITAN", "Enterprise Asset Management", "ONLINE"),
    ("MIDAS", "Finance", "ONLINE"),
    ("NOVA", "Data & Analytics", "ONLINE"),
    ("HERMES", "Communications", "ONLINE"),
    ("NEMSIS", "Emergency Management", "ONLINE"),
    ("HORUS", "UAS / Aerial Operations", "ONLINE"),
]

@app.get("/", response_class=HTMLResponse)
def dashboard():
    cards = "".join(f'''<article class="card"><div><span class="dot"></span><b>UNG-{sid}</b></div><h3>{name}</h3><p class="ok">{status}</p></article>''' for sid,name,status in SYSTEMS)
    return f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNG-ATLAS</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#08111f;color:#eaf2ff;font-family:Inter,system-ui,-apple-system,sans-serif}}header{{padding:22px 24px;border-bottom:1px solid #20314a;background:#0b1728;display:flex;justify-content:space-between;align-items:center}}.brand{{font-weight:900;font-size:22px;letter-spacing:.8px}}.sub{{color:#8da4c2;font-size:12px;margin-top:4px}}.live{{font-size:12px;color:#64e6a4;border:1px solid #245c45;padding:8px 11px;border-radius:999px}}main{{max-width:1180px;margin:auto;padding:24px}}.hero{{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:18px}}.panel,.card{{background:#0e1c30;border:1px solid #213653;border-radius:16px;padding:18px}}h1{{font-size:28px;margin:0 0 8px}}h2{{font-size:14px;color:#9bb1ce;text-transform:uppercase;letter-spacing:1px;margin:0 0 14px}}.metric{{font-size:34px;font-weight:800}}.muted{{color:#8298b6}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card b{{font-size:14px}}.card h3{{font-size:15px;margin:16px 0 6px;color:#b7c8dd}}.dot{{display:inline-block;width:8px;height:8px;background:#45d68a;border-radius:50%;margin-right:8px;box-shadow:0 0 10px #45d68a}}.ok{{color:#62e6a3;font-size:12px;font-weight:800;margin:0}}.deps{{display:flex;gap:10px;flex-wrap:wrap}}.dep{{background:#101f34;border:1px solid #29415f;padding:10px 13px;border-radius:10px;font-size:13px}}footer{{padding:18px 0;color:#637b9a;font-size:11px}}@media(max-width:700px){{.hero{{grid-template-columns:1fr}}.grid{{grid-template-columns:1fr}}header{{padding:18px}}main{{padding:16px}}h1{{font-size:23px}}}}
</style></head><body><header><div><div class="brand">UNG-ATLAS</div><div class="sub">National Grid Control Infrastructure</div></div><div class="live">● CONTROL PLANE ONLINE</div></header><main><section class="hero"><div class="panel"><h2>Operations Command</h2><h1>Enterprise Control Plane</h1><p class="muted">Central registry, system coordination, dependency visibility and operational control for the Uganda National Grid platform.</p><div class="deps"><span class="dep">JANUS · CONNECTED</span><span class="dep">PULSAR · CONNECTED</span><span class="dep">ATLAS · ACTIVE</span></div></div><div class="panel"><h2>Activation Wave</h2><div class="metric">6 / 6</div><div class="muted">Production systems online</div></div></section><h2>System Registry</h2><section class="grid">{cards}</section><footer>UNG-ATLAS v{VERSION} · Control Infrastructure</footer></main></body></html>'''

@app.get("/health")
def health():
    return {"status": "ok", "service": SYSTEM_ID, "version": VERSION}

@app.get("/ready")
def ready():
    return {"status": "ready", "service": SYSTEM_ID, "dependencies": {"janus": "configured", "pulsar": "configured"}, "version": VERSION}

@app.get("/v1/system")
def system():
    return {"system": SYSTEM_ID, "role": "enterprise control plane", "capabilities": ["service_registry","system_status","control_policy","dependency_coordination"], "version": VERSION}

@app.get("/v1/registry")
def registry():
    return {"systems": [{"id": f"UNG-{sid}", "name": name, "status": status.lower()} for sid,name,status in SYSTEMS], "count": len(SYSTEMS)}
