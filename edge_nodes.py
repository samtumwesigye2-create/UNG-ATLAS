from datetime import datetime, timezone
from threading import Lock
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix='/v1/edge', tags=['edge'])
_lock = Lock()
_nodes = {}

def now(): return datetime.now(timezone.utc).isoformat()

class NodeHeartbeat(BaseModel):
    node_id: str = Field(min_length=3, max_length=80)
    version: str = ''
    role: str = 'field-gateway'
    status: str = 'online'
    uptime_seconds: int = 0
    temperature_c: float | None = None
    events: int = 0
    queued: int = 0
    delivered: int = 0
    retrying: int = 0
    disk_free_bytes: int = 0
    janus: bool = False
    nexus: bool = False
    pulsar: bool = False

@router.post('/heartbeat')
def heartbeat(p: NodeHeartbeat):
    record = p.model_dump()
    record['last_seen'] = now()
    with _lock: _nodes[p.node_id] = record
    return {'accepted': True, 'node': record}

@router.get('/nodes')
def nodes():
    with _lock: items = list(_nodes.values())
    return {'nodes': items, 'total': len(items), 'timestamp': now()}

@router.get('/nodes/{node_id}')
def node(node_id: str):
    with _lock: item = _nodes.get(node_id)
    if not item: raise HTTPException(404, 'edge_node_not_found')
    return item
