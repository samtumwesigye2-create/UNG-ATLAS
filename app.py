from fastapi import FastAPI

SYSTEM_ID = "UNG-ATLAS"
VERSION = "0.1.0"

app = FastAPI(title="UNG-ATLAS Control Infrastructure", version=VERSION)

@app.get("/")
def root():
    return {"system": SYSTEM_ID, "name": "Control Infrastructure", "version": VERSION}

@app.get("/health")
def health():
    return {"status": "ok", "service": SYSTEM_ID, "version": VERSION}

@app.get("/ready")
def ready():
    return {"status": "ready", "service": SYSTEM_ID, "version": VERSION}

@app.get("/v1/system")
def system():
    return {
        "system": SYSTEM_ID,
        "role": "enterprise control plane",
        "capabilities": [
            "service_registry",
            "system_status",
            "control_policy",
            "dependency_coordination"
        ],
        "version": VERSION,
    }
