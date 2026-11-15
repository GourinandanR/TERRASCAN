"""TERRASCAN Stage 12 API. Stores evidence; does not manufacture science."""
from __future__ import annotations
import json, math, re, uuid, os, hmac, time, threading
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .database import initialize, transaction
from .auth import create_auth_tables, hash_password, verify_password, issue_token, token_digest, token_expiry, token_is_expired, utc_now
from .reporting import collect_report_data, build_csv, build_pdf
from .scenarios import plan_scenario
from .risks import assess_risks

@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize()
    with transaction() as conn:
        create_auth_tables(conn)
    yield

app = FastAPI(title="TERRASCAN API", version="3.2.0", description="Provenance-aware planetary analog research API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in __import__('os').getenv('TERRASCAN_CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()], allow_credentials=False, allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'], allow_headers=['Authorization','Content-Type'])


_rate_lock = threading.Lock()
_rate_events: dict[str, list[float]] = {}

@app.middleware("http")
async def security_headers_and_auth_throttle(request, call_next):
    path = request.url.path
    if path in {"/api/auth/login", "/api/auth/register"}:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"
        now_mono = time.monotonic()
        limit = int(os.getenv("TERRASCAN_LOGIN_RATE_LIMIT", "10"))
        with _rate_lock:
            events = [stamp for stamp in _rate_events.get(key, []) if now_mono - stamp < 60]
            if len(events) >= max(1, limit):
                from starlette.responses import JSONResponse
                response = JSONResponse({"detail":"Too many authentication attempts; retry later"}, status_code=429)
                response.headers["Retry-After"] = "60"
                return response
            events.append(now_mono)
            _rate_events[key] = events
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if path.startswith("/api/auth/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _configured_api_keys() -> dict[str, str]:
    """Load static API keys as key:role pairs; roles are read or admin."""
    parsed = {}
    for item in os.getenv("TERRASCAN_API_KEYS", "").split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise RuntimeError("TERRASCAN_API_KEYS entries must use key:role format")
        secret, role = item.rsplit(":", 1)
        if len(secret) < 32 or role not in {"read", "admin"}:
            raise RuntimeError("API keys must be at least 32 characters and use read/admin role")
        parsed[secret] = role
    return parsed

@app.middleware("http")
async def api_key_authentication(request, call_next):
    # Liveness/readiness remain public for orchestrator probes. Auth can be
    # disabled only for local development; deployment examples enable it.
    if request.url.path in {"/api/health", "/api/ready"} or request.url.path.startswith("/api/auth/") or request.method == "OPTIONS":
        return await call_next(request)
    if os.getenv("TERRASCAN_AUTH_REQUIRED", "false").lower() not in {"1", "true", "yes"}:
        return await call_next(request)
    keys = _configured_api_keys()
    if not keys:
        from starlette.responses import JSONResponse
        return JSONResponse({"detail": "API authentication is enabled but no API keys are configured"}, status_code=503)
    header = request.headers.get("authorization", "")
    scheme, _, supplied = header.partition(" ")
    if scheme.lower() != "bearer" or not supplied:
        from starlette.responses import JSONResponse
        return JSONResponse({"detail": "Bearer API key required"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
    role = None
    # Compare every configured key to avoid early-exit key matching.
    for secret, configured_role in keys.items():
        if hmac.compare_digest(supplied, secret):
            role = configured_role
    write_method = request.method not in {"GET", "HEAD"}
    if role is None or (write_method and role != "admin"):
        from starlette.responses import JSONResponse
        return JSONResponse({"detail": "Insufficient API credentials"}, status_code=403 if role else 401)
    request.state.api_role = role
    return await call_next(request)



def now() -> str: return datetime.now(timezone.utc).isoformat()
def uid() -> str: return str(uuid.uuid4())
def dump(v: Any) -> str: return json.dumps(v, separators=(',', ':'), allow_nan=False)
def record(row):
    if row is None: return None
    d = dict(row)
    for key in ('payload_json','input_snapshot_json','result_json'):
        if key in d and d[key] is not None:
            d['metadata' if key == 'payload_json' else key.removesuffix('_json')] = json.loads(d.pop(key))
    return d
def audit(conn, typ, ident, action, details):
    conn.execute('INSERT INTO audit_events(entity_type,entity_id,action,details_json,created_at) VALUES(?,?,?,?,?)',(typ,ident,action,dump(details),now()))

class ManifestIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str | None = None
    dataset_id: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    sha256: str
    source_uri: str
    review_status: Literal['pending-human-review','approved','rejected'] = 'pending-human-review'
    metadata: dict[str, Any] = Field(default_factory=dict)
    @field_validator('sha256')
    @classmethod
    def valid_hash(cls,v):
        if not re.fullmatch(r'[a-fA-F0-9]{64}',v): raise ValueError('sha256 must be exactly 64 hexadecimal characters')
        return v.lower()
    @field_validator('review_status')
    @classmethod
    def require_human_review(cls,v):
        if v != 'pending-human-review': raise ValueError('new manifests must enter pending-human-review; use the review endpoint for decisions')
        return v
    @field_validator('source_uri')
    @classmethod
    def safe_uri(cls,v):
        p=urlparse(v)
        if p.scheme not in ('https','file') or (p.scheme=='https' and not p.netloc): raise ValueError('source_uri must be a valid HTTPS or local file URI')
        return v

class ObservationIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str | None = None
    site_id: str = Field(min_length=1, max_length=120)
    target_body: Literal['Earth','Moon','Mars']
    criterion: str = Field(min_length=1, max_length=100)
    value: float
    unit: str = Field(min_length=1, max_length=40)
    manifest_id: str
    quality: str = Field(min_length=1, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)
    @field_validator('value')
    @classmethod
    def finite(cls,v):
        if not math.isfinite(v): raise ValueError('value must be finite')
        return v

class TargetProfileIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str | None = None
    target_body: Literal['Moon','Mars']
    feature_key: str = Field(min_length=1, max_length=100)
    value: float
    unit: str = Field(min_length=1, max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)
    @field_validator('value')
    @classmethod
    def finite(cls,v):
        if not math.isfinite(v): raise ValueError('value must be finite')
        return v

class ReviewIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['approved','rejected']
    reason: str = Field(min_length=10, max_length=2000)
    reviewer: str = Field(min_length=1, max_length=120)

class RunIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    target_body: Literal['Moon','Mars']
    filters: dict[str, Any] = Field(default_factory=dict)


def _get_session_user(request: Request):
    scheme, _, raw = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not raw:
        return None
    with transaction() as conn:
        row = conn.execute(
            """SELECT u.id,u.username,u.role,u.active,s.expires_at,s.revoked_at
               FROM user_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?""",
            (token_digest(raw),)).fetchone()
    if not row or not row["active"] or row["revoked_at"] or token_is_expired(row["expires_at"]):
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}

@app.post("/api/auth/register")
def register_user(payload: dict):
    username, password = str(payload.get("username", "")).strip(), str(payload.get("password", ""))
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        raise HTTPException(422, "Username must be 3–32 valid characters")
    try:
        salt, pwhash = hash_password(password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    with transaction() as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            raise HTTPException(403, "Initial administrator already exists")
        conn.execute("INSERT INTO users(username,password_salt,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                     (username,salt,pwhash,"admin",utc_now()))
        user_id = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()[0]
        raw, digest = issue_token()
        conn.execute("INSERT INTO user_sessions(user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)",
                     (user_id,digest,token_expiry(),utc_now()))
    return {"access_token":raw,"token_type":"bearer","expires_in":43200,
            "user":{"id":user_id,"username":username,"role":"admin"}}

@app.post("/api/auth/login")
def login_user(payload: dict):
    username, password = str(payload.get("username","")).strip(), str(payload.get("password",""))
    with transaction() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row or not row["active"] or not verify_password(password,row["password_salt"],row["password_hash"]):
            raise HTTPException(401,"Invalid username or password")
        raw,digest = issue_token()
        conn.execute("INSERT INTO user_sessions(user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)",
                     (row["id"],digest,token_expiry(),utc_now()))
    return {"access_token":raw,"token_type":"bearer","expires_in":43200,
            "user":{"id":row["id"],"username":row["username"],"role":row["role"]}}

@app.get("/api/auth/me")
def current_user(request: Request):
    user = _get_session_user(request)
    if not user: raise HTTPException(401,"Valid user session required")
    return {"user":user}

@app.post("/api/auth/logout")
def logout_user(request: Request):
    scheme, _, raw = request.headers.get("authorization","").partition(" ")
    if scheme.lower() != "bearer" or not raw: raise HTTPException(401,"Valid session required")
    with transaction() as conn:
        conn.execute("UPDATE user_sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                     (utc_now(),token_digest(raw)))
    return {"status":"logged_out"}

@app.get("/api/auth/users")
def list_users(request: Request):
    actor = _get_session_user(request)
    if not actor: raise HTTPException(401,"Login required")
    if actor["role"] != "admin": raise HTTPException(403,"Administrator role required")
    with transaction() as conn:
        rows = conn.execute("SELECT id,username,role,active,created_at FROM users ORDER BY id").fetchall()
    return {"users":[dict(row) for row in rows]}

@app.post("/api/auth/users")
def add_user(payload: dict, request: Request):
    actor = _get_session_user(request)
    if not actor: raise HTTPException(401,"Login required")
    if actor["role"] != "admin": raise HTTPException(403,"Administrator role required")
    username, role = str(payload.get("username","")).strip(), str(payload.get("role","viewer"))
    if role not in {"viewer","analyst","admin"}: raise HTTPException(422,"Invalid role")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}",username): raise HTTPException(422,"Invalid username")
    try: salt,pwhash = hash_password(str(payload.get("password","")))
    except ValueError as exc: raise HTTPException(422,str(exc))
    with transaction() as conn:
        try:
            conn.execute("INSERT INTO users(username,password_salt,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                         (username,salt,pwhash,role,utc_now()))
        except Exception: raise HTTPException(409,"Username already exists")
        user_id = conn.execute("SELECT id FROM users WHERE username=?",(username,)).fetchone()[0]
    return {"id":user_id,"username":username,"role":role}

@app.patch("/api/auth/users/{user_id}")
def change_user(user_id: int, payload: dict, request: Request):
    actor = _get_session_user(request)
    if not actor: raise HTTPException(401,"Login required")
    if actor["role"] != "admin": raise HTTPException(403,"Administrator role required")
    role, active = payload.get("role"), payload.get("active")
    if role is not None and role not in {"viewer","analyst","admin"}: raise HTTPException(422,"Invalid role")
    with transaction() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=?",(user_id,)).fetchone():
            raise HTTPException(404,"User not found")
        if user_id == actor["id"] and active is False:
            raise HTTPException(409,"Cannot deactivate current administrator")
        if role is not None: conn.execute("UPDATE users SET role=? WHERE id=?",(role,user_id))
        if active is not None:
            conn.execute("UPDATE users SET active=? WHERE id=?",(int(bool(active)),user_id))
            if not active:
                conn.execute("UPDATE user_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",(utc_now(),user_id))
    return {"status":"updated","user_id":user_id}

@app.middleware("http")
async def user_session_authorization(request, call_next):
    if request.url.path.startswith("/api/auth/") or request.url.path in {"/api/health","/api/ready"} or request.method == "OPTIONS":
        return await call_next(request)
    if os.getenv("TERRASCAN_USER_AUTH_REQUIRED","false").lower() not in {"1","true","yes"}:
        return await call_next(request)
    user = _get_session_user(request)
    if not user:
        from starlette.responses import JSONResponse
        return JSONResponse({"detail":"User login required"},status_code=401)
    if request.method not in {"GET","HEAD"} and user["role"] not in {"analyst","admin"}:
        from starlette.responses import JSONResponse
        return JSONResponse({"detail":"Analyst or administrator role required"},status_code=403)
    request.state.user = user
    return await call_next(request)

@app.get('/api/health')
def health():
    # Liveness: the process is responsive. Dependency checks belong to /api/ready.
    return {'status':'ok','service':'terrascan-api','version':'3.1.0'}

@app.get('/api/ready')
def ready():
    # Readiness: confirm the configured SQLite dependency is reachable.
    try:
        with transaction() as c:
            c.execute('SELECT 1')
        return {'status':'ready','service':'terrascan-api','version':'3.1.0','database':'connected'}
    except Exception:
        raise HTTPException(503, 'Database is not ready')

@app.post('/api/manifests', status_code=201)
def create_manifest(data: ManifestIn):
    ident=data.id or uid(); created=now()
    with transaction() as c:
        try: c.execute('INSERT INTO dataset_manifests VALUES(?,?,?,?,?,?,?,?)',(ident,data.dataset_id,data.version,data.sha256,data.source_uri,data.review_status,dump(data.metadata),created))
        except Exception as e:
            if 'UNIQUE constraint' in str(e): raise HTTPException(409,'Manifest with this dataset_id and checksum already exists')
            raise
        audit(c,'manifest',ident,'created',{'review_status':data.review_status,'sha256':data.sha256})
        return record(c.execute('SELECT * FROM dataset_manifests WHERE id=?',(ident,)).fetchone())

@app.get('/api/manifests')
def list_manifests(limit:int=Query(100,ge=1,le=500), offset:int=Query(0,ge=0)):
    with transaction() as c: return {'items':[record(r) for r in c.execute('SELECT * FROM dataset_manifests ORDER BY created_at DESC LIMIT ? OFFSET ?',(limit,offset))], 'limit':limit,'offset':offset}

@app.get('/api/manifests/{ident}')
def get_manifest(ident:str):
    with transaction() as c: r=c.execute('SELECT * FROM dataset_manifests WHERE id=?',(ident,)).fetchone()
    if not r: raise HTTPException(404,'Manifest not found')
    return record(r)

@app.post('/api/observations', status_code=201)
def create_observation(data: ObservationIn):
    ident=data.id or uid(); created=now()
    with transaction() as c:
        m=c.execute('SELECT review_status FROM dataset_manifests WHERE id=?',(data.manifest_id,)).fetchone()
        if not m: raise HTTPException(422,'Referenced manifest does not exist')
        if m['review_status']!='approved': raise HTTPException(409,'Evidence cannot be registered until its source manifest is approved')
        c.execute('''INSERT INTO observations
          (id,site_id,target_body,criterion,value,unit,manifest_id,quality,payload_json,created_at,review_status)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
          (ident,data.site_id,data.target_body,data.criterion,data.value,data.unit,data.manifest_id,data.quality,dump(data.metadata),created,'pending-human-review'))
        audit(c,'observation',ident,'created',{'manifest_id':data.manifest_id})
        return record(c.execute('SELECT * FROM observations WHERE id=?',(ident,)).fetchone())

@app.get('/api/observations')
def list_observations(site_id:str|None=None, limit:int=Query(200,ge=1,le=1000)):
    with transaction() as c:
        if site_id: rows=c.execute('SELECT * FROM observations WHERE site_id=? ORDER BY created_at DESC LIMIT ?',(site_id,limit))
        else: rows=c.execute('SELECT * FROM observations ORDER BY created_at DESC LIMIT ?',(limit,))
        return {'items':[record(r) for r in rows]}

@app.post('/api/target-profiles', status_code=201)
def create_target_profile(data: TargetProfileIn):
    ident=data.id or uid(); created=now()
    with transaction() as c:
        try: c.execute('INSERT INTO target_profiles VALUES(?,?,?,?,?,?,?)',(ident,data.target_body,data.feature_key,data.value,data.unit,dump(data.metadata),created))
        except Exception as e:
            if 'UNIQUE constraint' in str(e): raise HTTPException(409,'Target feature already exists; use a new profile after reviewing the existing record')
            raise
        audit(c,'target-profile',ident,'created',{'target_body':data.target_body,'feature_key':data.feature_key})
        return record(c.execute('SELECT * FROM target_profiles WHERE id=?',(ident,)).fetchone())

@app.get('/api/target-profiles')
def list_target_profiles(target_body:Literal['Moon','Mars']|None=None):
    with transaction() as c:
        rows=c.execute('SELECT * FROM target_profiles WHERE target_body=? ORDER BY feature_key',(target_body,)) if target_body else c.execute('SELECT * FROM target_profiles ORDER BY target_body,feature_key')
        return {'items':[record(r) for r in rows]}

@app.get('/api/review-queue')
def review_queue(limit:int=Query(200,ge=1,le=1000)):
    with transaction() as c:
        manifests=[record(r) for r in c.execute(
            "SELECT * FROM dataset_manifests WHERE review_status='pending-human-review' ORDER BY created_at LIMIT ?",(limit,))]
        observations=[record(r) for r in c.execute(
            "SELECT * FROM observations WHERE review_status='pending-human-review' ORDER BY created_at LIMIT ?",(limit,))]
        return {"manifests":manifests,"observations":observations,
                "counts":{"manifests":len(manifests),"observations":len(observations)}}

@app.post('/api/manifests/{ident}/review')
def review_manifest(ident:str, data:ReviewIn):
    reviewed=now()
    with transaction() as c:
        row=c.execute('SELECT * FROM dataset_manifests WHERE id=?',(ident,)).fetchone()
        if not row: raise HTTPException(404,'Manifest not found')
        if row['review_status']!='pending-human-review':
            raise HTTPException(409,'Manifest has already been reviewed; create a new version to change its decision')
        c.execute('UPDATE dataset_manifests SET review_status=? WHERE id=?',(data.decision,ident))
        c.execute('INSERT INTO review_events(entity_type,entity_id,decision,reason,reviewer,created_at) VALUES(?,?,?,?,?,?)',
                  ('manifest',ident,data.decision,data.reason.strip(),data.reviewer.strip(),reviewed))
        audit(c,'manifest',ident,'reviewed',{'decision':data.decision,'reason':data.reason.strip(),'reviewer':data.reviewer.strip()})
        return record(c.execute('SELECT * FROM dataset_manifests WHERE id=?',(ident,)).fetchone())

@app.post('/api/observations/{ident}/review')
def review_observation(ident:str, data:ReviewIn):
    reviewed=now()
    with transaction() as c:
        row=c.execute('SELECT * FROM observations WHERE id=?',(ident,)).fetchone()
        if not row: raise HTTPException(404,'Observation not found')
        if row['review_status']!='pending-human-review':
            raise HTTPException(409,'Observation has already been reviewed; create a corrected record instead')
        manifest=c.execute('SELECT review_status FROM dataset_manifests WHERE id=?',(row['manifest_id'],)).fetchone()
        if data.decision=='approved' and (not manifest or manifest['review_status']!='approved'):
            raise HTTPException(409,'Observation cannot be approved while its source manifest is not approved')
        c.execute('UPDATE observations SET review_status=?,reviewed_at=?,reviewer=?,review_reason=? WHERE id=?',
                  (data.decision,reviewed,data.reviewer.strip(),data.reason.strip(),ident))
        c.execute('INSERT INTO review_events(entity_type,entity_id,decision,reason,reviewer,created_at) VALUES(?,?,?,?,?,?)',
                  ('observation',ident,data.decision,data.reason.strip(),data.reviewer.strip(),reviewed))
        audit(c,'observation',ident,'reviewed',{'decision':data.decision,'reason':data.reason.strip(),'reviewer':data.reviewer.strip()})
        return record(c.execute('SELECT * FROM observations WHERE id=?',(ident,)).fetchone())

@app.get('/api/review-history')
def review_history(limit:int=Query(200,ge=1,le=1000)):
    with transaction() as c:
        rows=c.execute('SELECT * FROM review_events ORDER BY created_at DESC LIMIT ?',(limit,))
        return {'items':[dict(r) for r in rows]}

@app.post('/api/comparison-runs', status_code=201)
def create_comparison_run(data: RunIn):
    ident=uid(); created=now()
    with transaction() as c:
        # Snapshot only approved, stored evidence and target references; no scoring is fabricated here.
        obs=[record(r) for r in c.execute("SELECT * FROM observations WHERE target_body='Earth' AND review_status='approved' ORDER BY created_at")]
        refs=[record(r) for r in c.execute('SELECT * FROM target_profiles WHERE target_body=? ORDER BY feature_key',(data.target_body,))]
        snapshot={'filters':data.filters,'observations':obs,'target_profiles':refs,'scoring_status':'not-computed-by-api'}
        c.execute('INSERT INTO comparison_runs VALUES(?,?,?,?,?,?,?)',(ident,data.target_body,'queued',dump(snapshot),None,created,None))
        audit(c,'comparison-run',ident,'created',{'target_body':data.target_body,'observation_count':len(obs),'reference_count':len(refs)})
        return record(c.execute('SELECT * FROM comparison_runs WHERE id=?',(ident,)).fetchone())

@app.get('/api/comparison-runs')
def list_comparison_runs(limit:int=Query(100,ge=1,le=500)):
    with transaction() as c: return {'items':[record(r) for r in c.execute('SELECT * FROM comparison_runs ORDER BY created_at DESC LIMIT ?',(limit,))]}


@app.get('/api/reports/{target_body}/summary')
def report_summary(target_body:Literal['Moon','Mars']):
    with transaction() as c:
        return collect_report_data(c,target_body)

@app.get('/api/reports/{target_body}/csv')
def report_csv(target_body:Literal['Moon','Mars']):
    with transaction() as c: data=collect_report_data(c,target_body)
    content=build_csv(data)
    return Response(content=content,media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':f'attachment; filename="terrascan-{target_body.lower()}-evidence-report.csv"'})

@app.get('/api/reports/{target_body}/pdf')
def report_pdf(target_body:Literal['Moon','Mars']):
    with transaction() as c: data=collect_report_data(c,target_body)
    try: content=build_pdf(data)
    except RuntimeError as exc: raise HTTPException(503,str(exc))
    return Response(content=content,media_type='application/pdf',
                    headers={'Content-Disposition':f'attachment; filename="terrascan-{target_body.lower()}-evidence-report.pdf"'})

@app.get('/api/audit')
def list_audit(limit:int=Query(100,ge=1,le=500)):
    with transaction() as c: return {'items':[dict(r) for r in c.execute('SELECT * FROM audit_events ORDER BY id DESC LIMIT ?',(limit,))]}

# Stage 17: constraint-gate suitability is independent of analog similarity.
class MissionCriterion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=40)
    minimum: float | None = None
    maximum: float | None = None
    required: bool = True
    description: str = Field(default='', max_length=500)
    @field_validator('minimum', 'maximum')
    @classmethod
    def finite_bound(cls, value):
        if value is not None and not math.isfinite(value): raise ValueError('constraint bounds must be finite')
        return value

class MissionProfileIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    target_body: Literal['Earth','Moon','Mars']
    description: str = Field(default='', max_length=2000)
    criteria: list[MissionCriterion] = Field(min_length=1, max_length=50)
    validation_state: Literal['user-configured-unvalidated'] = 'user-configured-unvalidated'
    @field_validator('criteria')
    @classmethod
    def unique_keys_and_bounds(cls, values):
        keys=[v.key for v in values]
        if len(keys)!=len(set(keys)): raise ValueError('criterion keys must be unique')
        for v in values:
            if v.minimum is not None and v.maximum is not None and v.minimum > v.maximum:
                raise ValueError(f'{v.key}: minimum cannot exceed maximum')
        return values

class SuitabilityRunIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile_id: str
    profile_revision: int = Field(ge=1)
    site_id: str = Field(min_length=1, max_length=120)

@app.post('/api/mission-profiles', status_code=201)
def create_mission_profile(data: MissionProfileIn):
    ident=data.id or uid(); created=now()
    with transaction() as c:
        revision=c.execute('SELECT COALESCE(MAX(revision),0)+1 AS n FROM mission_profiles WHERE id=?',(ident,)).fetchone()['n']
        c.execute('INSERT INTO mission_profiles(id,revision,name,target_body,description,criteria_json,validation_state,created_at) VALUES(?,?,?,?,?,?,?,?)',
                  (ident,revision,data.name,data.target_body,data.description,dump([x.model_dump() for x in data.criteria]),data.validation_state,created))
        audit(c,'mission-profile',ident,'revision-created',{'revision':revision,'criteria_count':len(data.criteria),'validation_state':data.validation_state})
        return {'id':ident,'revision':revision,'name':data.name,'target_body':data.target_body,'description':data.description,
                'criteria':[x.model_dump() for x in data.criteria],'validation_state':data.validation_state,'created_at':created}

@app.get('/api/mission-profiles')
def list_mission_profiles():
    with transaction() as c: rows=c.execute('SELECT * FROM mission_profiles ORDER BY name,revision DESC').fetchall()
    return {'items':[{'id':r['id'],'revision':r['revision'],'name':r['name'],'target_body':r['target_body'],
      'description':r['description'],'criteria':json.loads(r['criteria_json']),'validation_state':r['validation_state'],'created_at':r['created_at']} for r in rows]}

@app.post('/api/suitability-assessments', status_code=201)
def create_suitability_assessment(data: SuitabilityRunIn):
    ident=uid(); created=now()
    with transaction() as c:
        p=c.execute('SELECT * FROM mission_profiles WHERE id=? AND revision=?',(data.profile_id,data.profile_revision)).fetchone()
        if not p: raise HTTPException(404,'Mission profile revision not found')
        criteria=json.loads(p['criteria_json'])
        rows=c.execute("""SELECT o.*,m.sha256,m.dataset_id,m.version,m.source_uri,m.review_status AS manifest_review_status
          FROM observations o JOIN dataset_manifests m ON m.id=o.manifest_id
          WHERE o.site_id=? AND o.target_body=? AND o.review_status='approved' AND m.review_status='approved'
          ORDER BY o.created_at,o.id""",(data.site_id,p['target_body'])).fetchall()
        evidence=[dict(r) for r in rows]; outcomes=[]
        for criterion in criteria:
            matches=[o for o in evidence if o['criterion']==criterion['key']]
            if not criterion['required'] and not matches:
                outcomes.append({'key':criterion['key'],'status':'not-applicable','reason':'Optional criterion has no approved evidence','evidence_ids':[],'unit':criterion['unit']}); continue
            if not matches:
                outcomes.append({'key':criterion['key'],'status':'unknown','reason':'No approved observation is available','evidence_ids':[],'unit':criterion['unit']}); continue
            compatible=[o for o in matches if o['unit'].strip().lower()==criterion['unit'].strip().lower()]
            if not compatible:
                outcomes.append({'key':criterion['key'],'status':'unknown','reason':'Evidence unit does not exactly match configured unit; no implicit conversion is performed','evidence_ids':[o['id'] for o in matches],'unit':criterion['unit']}); continue
            values=[o['value'] for o in compatible]
            failed=any((criterion['minimum'] is not None and v < criterion['minimum']) or (criterion['maximum'] is not None and v > criterion['maximum']) for v in values)
            outcomes.append({'key':criterion['key'],'status':'fail' if failed else 'pass',
              'reason':'At least one approved measurement is outside configured inclusive bounds' if failed else 'All matching approved measurements are within configured inclusive bounds',
              'evidence_ids':[o['id'] for o in compatible],'values':values,'unit':criterion['unit'],
              'minimum':criterion['minimum'],'maximum':criterion['maximum']})
        required=[x for x in outcomes if next(c for c in criteria if c['key']==x['key'])['required']]
        status='ineligible' if any(x['status']=='fail' for x in required) else ('indeterminate' if any(x['status']=='unknown' for x in required) else 'eligible')
        snapshot={'profile_id':p['id'],'profile_revision':p['revision'],'profile_validation_state':p['validation_state'],
          'site_id':data.site_id,'target_body':p['target_body'],'criteria':criteria,'approved_evidence':evidence,
          'policy':'Unknown required constraints fail closed; units require exact match; no implicit conversions.'}
        result={'status':status,'constraints':outcomes,'interpretation':'Constraint-gate result only. Not a landing-safety certification or mission authorization. Profile thresholds are user-configured and unvalidated.'}
        c.execute('INSERT INTO suitability_assessments VALUES(?,?,?,?,?,?,?,?,?)',(ident,p['id'],p['revision'],data.site_id,p['target_body'],status,dump(snapshot),dump(result),created))
        audit(c,'suitability-assessment',ident,'created',{'profile_id':p['id'],'profile_revision':p['revision'],'site_id':data.site_id,'status':status,'evidence_count':len(evidence)})
        return {'id':ident,'profile_id':p['id'],'profile_revision':p['revision'],'site_id':data.site_id,'target_body':p['target_body'],'status':status,'input_snapshot':snapshot,'result':result,'created_at':created}

@app.get('/api/suitability-assessments')
def list_suitability_assessments(limit:int=Query(100,ge=1,le=500)):
    with transaction() as c: rows=c.execute('SELECT * FROM suitability_assessments ORDER BY created_at DESC LIMIT ?',(limit,)).fetchall()
    return {'items':[{'id':r['id'],'profile_id':r['profile_id'],'profile_revision':r['profile_revision'],'site_id':r['site_id'],'target_body':r['target_body'],'status':r['status'],'input_snapshot':json.loads(r['input_snapshot_json']),'result':json.loads(r['result_json']),'created_at':r['created_at']} for r in rows]}

@app.get('/api/suitability-assessments/{ident}')
def get_suitability_assessment(ident:str):
    with transaction() as c: r=c.execute('SELECT * FROM suitability_assessments WHERE id=?',(ident,)).fetchone()
    if not r: raise HTTPException(404,'Suitability assessment not found')
    return {'id':r['id'],'profile_id':r['profile_id'],'profile_revision':r['profile_revision'],'site_id':r['site_id'],'target_body':r['target_body'],'status':r['status'],'input_snapshot':json.loads(r['input_snapshot_json']),'result':json.loads(r['result_json']),'created_at':r['created_at']}


# Stage 18: hypothetical mission scenarios and dependency-based scheduling.
class ScenarioActivity(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    duration_hours: float = Field(ge=0, le=1_000_000)
    depends_on: list[str] = Field(default_factory=list, max_length=50)
    resources: dict[str, float] = Field(default_factory=dict)
    @field_validator('duration_hours')
    @classmethod
    def duration_finite(cls, v):
        if not math.isfinite(v): raise ValueError('duration_hours must be finite')
        return v
    @field_validator('resources')
    @classmethod
    def resources_finite_nonnegative(cls, v):
        if any(not math.isfinite(x) or x < 0 for x in v.values()): raise ValueError('resource quantities must be finite and non-negative')
        return v

class MissionScenarioIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=160)
    target_body: Literal['Earth','Moon','Mars']
    site_id: str = Field(min_length=1, max_length=120)
    suitability_assessment_id: str | None = None
    activities: list[ScenarioActivity] = Field(min_length=1, max_length=100)
    resource_limits: dict[str, float] = Field(default_factory=dict)
    @field_validator('resource_limits')
    @classmethod
    def limits_finite_nonnegative(cls, v):
        if any(not math.isfinite(x) or x < 0 for x in v.values()): raise ValueError('resource limits must be finite and non-negative')
        return v

@app.post('/api/mission-scenarios', status_code=201)
def create_mission_scenario(data: MissionScenarioIn):
    ident=uid(); created=now()
    activities=[x.model_dump() for x in data.activities]
    try: result=plan_scenario(activities,data.resource_limits)
    except ValueError as exc: raise HTTPException(422,str(exc))
    with transaction() as c:
        suitability=None
        if data.suitability_assessment_id:
            suitability=c.execute('SELECT * FROM suitability_assessments WHERE id=?',(data.suitability_assessment_id,)).fetchone()
            if not suitability: raise HTTPException(404,'Referenced suitability assessment not found')
            if suitability['site_id'] != data.site_id or suitability['target_body'] != data.target_body:
                raise HTTPException(422,'Suitability assessment site and target body must match scenario')
        suitability_status=suitability['status'] if suitability else 'not-provided'
        snapshot={'name':data.name,'target_body':data.target_body,'site_id':data.site_id,
          'suitability_assessment_id':data.suitability_assessment_id,'suitability_status_at_creation':suitability_status,
          'activities':activities,'resource_limits':data.resource_limits,
          'assumption':'All durations, dependencies, resource quantities and limits are user-supplied hypothetical planning inputs.'}
        result['suitability_gate']='eligible' if suitability_status=='eligible' else ('blocked-or-uncertain' if suitability_status in ('ineligible','indeterminate') else 'not-assessed')
        result['operational_authorization']='not-assessed'
        c.execute('INSERT INTO mission_scenarios VALUES(?,?,?,?,?,?,?,?,?)',(ident,data.name,data.target_body,data.site_id,data.suitability_assessment_id,result['status'],dump(snapshot),dump(result),created))
        audit(c,'mission-scenario',ident,'created',{'target_body':data.target_body,'site_id':data.site_id,'status':result['status'],'activity_count':len(activities)})
        return {'id':ident,'name':data.name,'target_body':data.target_body,'site_id':data.site_id,
          'status':result['status'],'input_snapshot':snapshot,'result':result,'created_at':created}

@app.get('/api/mission-scenarios')
def list_mission_scenarios(limit:int=Query(100,ge=1,le=500)):
    with transaction() as c: rows=c.execute('SELECT * FROM mission_scenarios ORDER BY created_at DESC LIMIT ?',(limit,)).fetchall()
    return {'items':[{'id':r['id'],'name':r['name'],'target_body':r['target_body'],'site_id':r['site_id'],'status':r['status'],
      'input_snapshot':json.loads(r['input_snapshot_json']),'result':json.loads(r['result_json']),'created_at':r['created_at']} for r in rows]}

@app.get('/api/mission-scenarios/{ident}')
def get_mission_scenario(ident:str):
    with transaction() as c: r=c.execute('SELECT * FROM mission_scenarios WHERE id=?',(ident,)).fetchone()
    if not r: raise HTTPException(404,'Mission scenario not found')
    return {'id':r['id'],'name':r['name'],'target_body':r['target_body'],'site_id':r['site_id'],'status':r['status'],
      'input_snapshot':json.loads(r['input_snapshot_json']),'result':json.loads(r['result_json']),'created_at':r['created_at']}


# Stage 19: qualitative risk register and uncertainty-aware assessment snapshots.
class MissionRiskItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    risk_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category: str = Field(min_length=1, max_length=80)
    likelihood: Literal['rare','unlikely','possible','likely','unknown']
    impact: Literal['negligible','minor','moderate','major','severe','unknown']
    uncertainty: Literal['measured','estimated','inferred','unknown']
    uncertainty_basis: str = Field(min_length=1, max_length=1000)
    mitigation: str = Field(default='', max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=30)

class MissionRiskAssessmentIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=160)
    target_body: Literal['Earth','Moon','Mars']
    site_id: str = Field(min_length=1, max_length=120)
    scenario_id: str | None = None
    risks: list[MissionRiskItem] = Field(min_length=1, max_length=100)

@app.post('/api/mission-risk-assessments', status_code=201)
def create_mission_risk_assessment(data: MissionRiskAssessmentIn):
    ident=uid(); created=now()
    risks=[x.model_dump() for x in data.risks]
    if len({x['risk_id'] for x in risks}) != len(risks):
        raise HTTPException(422,'risk_id values must be unique within an assessment')
    try: result=assess_risks(risks)
    except ValueError as exc: raise HTTPException(422,str(exc))
    with transaction() as c:
        scenario=None
        if data.scenario_id:
            scenario=c.execute('SELECT * FROM mission_scenarios WHERE id=?',(data.scenario_id,)).fetchone()
            if not scenario: raise HTTPException(404,'Referenced mission scenario not found')
            if scenario['site_id'] != data.site_id or scenario['target_body'] != data.target_body:
                raise HTTPException(422,'Scenario site and target body must match risk assessment')
        snapshot={'name':data.name,'target_body':data.target_body,'site_id':data.site_id,
                  'scenario_id':data.scenario_id,'risks':risks,
                  'scenario_snapshot':json.loads(scenario['input_snapshot_json']) if scenario else None,
                  'disclaimer':'Qualitative risk and uncertainty register; evidence references are user-supplied identifiers and are not automatically verified.'}
        c.execute('INSERT INTO mission_risk_assessments VALUES(?,?,?,?,?,?,?,?)',
                  (ident,data.name,data.target_body,data.site_id,data.scenario_id,dump(snapshot),dump(result),created))
        audit(c,'mission-risk-assessment',ident,'created',{'target_body':data.target_body,'site_id':data.site_id,
              'risk_count':len(risks),'overall_state':result['overall_state']})
    return {'id':ident,'name':data.name,'target_body':data.target_body,'site_id':data.site_id,
            'scenario_id':data.scenario_id,'input_snapshot':snapshot,'result':result,'created_at':created}

@app.get('/api/mission-risk-assessments')
def list_mission_risk_assessments(limit:int=Query(100,ge=1,le=500)):
    with transaction() as c:
        rows=c.execute('SELECT * FROM mission_risk_assessments ORDER BY created_at DESC LIMIT ?',(limit,)).fetchall()
    return {'items':[{'id':r['id'],'name':r['name'],'target_body':r['target_body'],'site_id':r['site_id'],
      'scenario_id':r['scenario_id'],'input_snapshot':json.loads(r['input_snapshot_json']),
      'result':json.loads(r['result_json']),'created_at':r['created_at']} for r in rows]}

@app.get('/api/mission-risk-assessments/{ident}')
def get_mission_risk_assessment(ident:str):
    with transaction() as c: r=c.execute('SELECT * FROM mission_risk_assessments WHERE id=?',(ident,)).fetchone()
    if not r: raise HTTPException(404,'Mission risk assessment not found')
    return {'id':r['id'],'name':r['name'],'target_body':r['target_body'],'site_id':r['site_id'],
      'scenario_id':r['scenario_id'],'input_snapshot':json.loads(r['input_snapshot_json']),
      'result':json.loads(r['result_json']),'created_at':r['created_at']}


# Stage 20: append-only human review, evidence-backed mitigation verification, and readiness overview.
class MissionRiskReviewIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    risk_id: str = Field(min_length=1, max_length=80)
    reviewer: str = Field(min_length=1, max_length=120)
    decision: Literal['acknowledged','action-required','mitigation-verified']
    rationale: str = Field(min_length=10, max_length=2000)
    mitigation_evidence_refs: list[str] = Field(default_factory=list, max_length=30)

def _resolve_approved_mitigation_evidence(conn, refs):
    if not refs:
        raise HTTPException(422,'Mitigation verification requires at least one approved evidence reference')
    resolved=[]
    for ref in refs:
        if ref.startswith('manifest:'):
            ident=ref.split(':',1)[1]
            row=conn.execute('SELECT id,sha256,review_status FROM dataset_manifests WHERE id=?',(ident,)).fetchone()
            if not row or row['review_status']!='approved':
                raise HTTPException(409,f'Manifest evidence is missing or not approved: {ident}')
            resolved.append({'reference':ref,'type':'manifest','id':row['id'],'sha256':row['sha256'],'review_status':'approved'})
        elif ref.startswith('observation:'):
            ident=ref.split(':',1)[1]
            row=conn.execute('SELECT o.id,o.review_status,o.manifest_id,m.sha256,m.review_status AS manifest_review_status FROM observations o JOIN dataset_manifests m ON m.id=o.manifest_id WHERE o.id=?',(ident,)).fetchone()
            if not row or row['review_status']!='approved' or row['manifest_review_status']!='approved':
                raise HTTPException(409,f'Observation or its source manifest is missing or not approved: {ident}')
            resolved.append({'reference':ref,'type':'observation','id':row['id'],'manifest_id':row['manifest_id'],'manifest_sha256':row['sha256'],'review_status':'approved','manifest_review_status':'approved'})
        else:
            raise HTTPException(422,'Evidence references must use manifest:<id> or observation:<id>')
    return resolved

@app.post('/api/mission-risk-assessments/{ident}/reviews', status_code=201)
def review_mission_risk(ident:str, data:MissionRiskReviewIn):
    review_id=uid(); created=now()
    with transaction() as c:
        assessment=c.execute('SELECT * FROM mission_risk_assessments WHERE id=?',(ident,)).fetchone()
        if not assessment: raise HTTPException(404,'Mission risk assessment not found')
        snapshot=json.loads(assessment['input_snapshot_json'])
        if not any(x['risk_id']==data.risk_id for x in snapshot['risks']):
            raise HTTPException(404,'Risk ID is not part of this assessment')
        evidence=[]
        if data.decision=='mitigation-verified':
            evidence=_resolve_approved_mitigation_evidence(c,data.mitigation_evidence_refs)
        elif data.mitigation_evidence_refs:
            evidence=_resolve_approved_mitigation_evidence(c,data.mitigation_evidence_refs)
        c.execute('INSERT INTO mission_risk_reviews (id,assessment_id,risk_id,reviewer,decision,rationale,mitigation_evidence_json,evidence_snapshot_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
          (review_id,ident,data.risk_id,data.reviewer,data.decision,data.rationale,dump(data.mitigation_evidence_refs),dump(evidence),created))
        audit(c,'mission-risk-review',review_id,'recorded',{'assessment_id':ident,'risk_id':data.risk_id,'decision':data.decision,'reviewer':data.reviewer,'verified_evidence_count':len(evidence)})
        return {'id':review_id,'assessment_id':ident,'risk_id':data.risk_id,'reviewer':data.reviewer,'decision':data.decision,'rationale':data.rationale,'mitigation_evidence':evidence,'created_at':created}

@app.get('/api/mission-risk-assessments/{ident}/reviews')
def list_mission_risk_reviews(ident:str):
    with transaction() as c:
        if not c.execute('SELECT 1 FROM mission_risk_assessments WHERE id=?',(ident,)).fetchone():
            raise HTTPException(404,'Mission risk assessment not found')
        rows=c.execute('SELECT * FROM mission_risk_reviews WHERE assessment_id=? ORDER BY created_at,id',(ident,)).fetchall()
    return {'items':[{'id':r['id'],'risk_id':r['risk_id'],'reviewer':r['reviewer'],'decision':r['decision'],'rationale':r['rationale'],'mitigation_evidence_refs':json.loads(r['mitigation_evidence_json']),'mitigation_evidence':json.loads(r['evidence_snapshot_json']),'created_at':r['created_at']} for r in rows]}

@app.get('/api/mission-readiness/{ident}')
def mission_readiness(ident:str):
    with transaction() as c:
        assessment=c.execute('SELECT * FROM mission_risk_assessments WHERE id=?',(ident,)).fetchone()
        if not assessment: raise HTTPException(404,'Mission risk assessment not found')
        snapshot=json.loads(assessment['input_snapshot_json'])
        rows=c.execute('SELECT r.* FROM mission_risk_reviews r JOIN (SELECT risk_id,MAX(created_at) AS latest_at FROM mission_risk_reviews WHERE assessment_id=? GROUP BY risk_id) x ON r.risk_id=x.risk_id AND r.created_at=x.latest_at WHERE r.assessment_id=?',(ident,ident)).fetchall()
        latest={row['risk_id']:row for row in rows}
    items=[]
    for risk in snapshot['risks']:
        review=latest.get(risk['risk_id'])
        decision=review['decision'] if review else 'unreviewed'
        items.append({'risk_id':risk['risk_id'],'title':risk['title'],'review_decision':decision,'reviewer':review['reviewer'] if review else None,'reviewed_at':review['created_at'] if review else None,'mitigation_evidence_count':len(json.loads(review['evidence_snapshot_json'])) if review else 0})
    if any(x['review_decision']=='action-required' for x in items): state='open-actions'
    elif any(x['review_decision']=='unreviewed' for x in items): state='review-incomplete'
    elif any(x['review_decision']!='mitigation-verified' for x in items): state='mitigations-not-verified'
    else: state='reviewed-mitigations-verified'
    return {'assessment_id':ident,'name':assessment['name'],'target_body':assessment['target_body'],'site_id':assessment['site_id'],'readiness_state':state,'items':items,'operational_authorization':'not-assessed','interpretation':'Readiness overview is a workflow status, not a mission authorization, safety case, or prediction of mission success.'}
