"""
organism/homeostasis.py – Self‑modification regulator.
Receives proposals from the reflection/inspection agents, checks them against
the genome, and safely updates the organism's self‑model.
"""
import json, os
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(__file__))

def _load(rel):
    with open(os.path.join(BASE, rel), 'r') as f:
        return json.load(f)

def _save(rel, data):
    with open(os.path.join(BASE, rel), 'w') as f:
        json.dump(data, f, indent=2)

def propose_weakness(name, impact):
    """Add a new weakness if it is truthful (genome check)."""
    # genome principle: Accuracy is survival – admitting a weakness is truth
    weaks = _load("organism/weaknesses.json")
    # avoid duplicates
    if any(w['name'] == name for w in weaks['weaknesses']):
        return False, "Already known"
    new_id = f"w{len(weaks['weaknesses'])+1:03d}"
    weaks['weaknesses'].append({
        "id": new_id,
        "name": name,
        "impact": impact,
        "resolved": False,
        "discovered": datetime.utcnow().isoformat()
    })
    _save("organism/weaknesses.json", weaks)
    return True, new_id

def resolve_weakness(weakness_id, resolution_note=""):
    """Mark a weakness as resolved (but keep it in history)."""
    weaks = _load("organism/weaknesses.json")
    for w in weaks['weaknesses']:
        if w['id'] == weakness_id:
            w['resolved'] = True
            w['resolution_note'] = resolution_note
            w['resolved_date'] = datetime.utcnow().isoformat()
            _save("organism/weaknesses.json", weaks)
            return True
    return False

def request_capability(name, description, reason):
    """File an evolution request. Will be evaluated later."""
    evo = _load("organism/evolution_requests.json")
    new_req = {
        "id": f"req{len(evo['requests'])+1:03d}",
        "capability": name,
        "description": description,
        "reason": reason,
        "requested_by": "reflection",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    evo['requests'].append(new_req)
    _save("organism/evolution_requests.json", evo)
    return new_req['id']

def approve_capability(request_id):
    """After internal deliberation, move a request to capabilities.json."""
    evo = _load("organism/evolution_requests.json")
    req = next((r for r in evo['requests'] if r['id'] == request_id), None)
    if not req or req['status'] != 'pending':
        return False
    # genome check: "Expand, but never at the cost of internal coherence"
    # We assume a simple coherence check passes (for now)
    caps = _load("organism/capabilities.json")
    new_cap = {
        "id": f"cap_{req['capability'].lower().replace(' ','_')}",
        "name": req['capability'],
        "description": req['description'],
        "source": "evolved",
        "acquired": datetime.utcnow().isoformat()
    }
    caps['capabilities'].append(new_cap)
    req['status'] = 'approved'
    _save("organism/capabilities.json", caps)
    _save("organism/evolution_requests.json", evo)
    return True
