"""SQLite persistence with explicit schema and per-request connections."""
from __future__ import annotations
import os, sqlite3
from pathlib import Path
from contextlib import contextmanager

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "terrascan.sqlite3"
DB_PATH = Path(os.getenv("TERRASCAN_DB_PATH", str(DEFAULT_DB))).expanduser()

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS dataset_manifests (
 id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, version TEXT NOT NULL,
 sha256 TEXT NOT NULL CHECK(length(sha256)=64), source_uri TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'pending-human-review'
   CHECK(review_status IN ('pending-human-review','approved','rejected')),
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(dataset_id, sha256)
);
CREATE TABLE IF NOT EXISTS observations (
 id TEXT PRIMARY KEY, site_id TEXT NOT NULL, target_body TEXT NOT NULL CHECK(target_body IN ('Earth','Moon','Mars')),
 criterion TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
 manifest_id TEXT NOT NULL REFERENCES dataset_manifests(id), quality TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS target_profiles (
 id TEXT PRIMARY KEY, target_body TEXT NOT NULL CHECK(target_body IN ('Moon','Mars')),
 feature_key TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(target_body, feature_key)
);
CREATE TABLE IF NOT EXISTS comparison_runs (
 id TEXT PRIMARY KEY, target_body TEXT NOT NULL CHECK(target_body IN ('Moon','Mars')),
 status TEXT NOT NULL CHECK(status IN ('queued','completed','failed')),
 input_snapshot_json TEXT NOT NULL, result_json TEXT, created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
 action TEXT NOT NULL, details_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_observations_site ON observations(site_id);
CREATE INDEX IF NOT EXISTS idx_observations_manifest ON observations(manifest_id);
CREATE INDEX IF NOT EXISTS idx_runs_created ON comparison_runs(created_at);
CREATE TABLE IF NOT EXISTS review_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL CHECK(entity_type IN ('manifest','observation')),
 entity_id TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('approved','rejected')),
 reason TEXT NOT NULL, reviewer TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_entity ON review_events(entity_type, entity_id, created_at);
CREATE TABLE IF NOT EXISTS mission_profiles (
 id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision >= 1), name TEXT NOT NULL,
 target_body TEXT NOT NULL CHECK(target_body IN ('Earth','Moon','Mars')),
 description TEXT NOT NULL, criteria_json TEXT NOT NULL, validation_state TEXT NOT NULL DEFAULT 'user-configured-unvalidated'
 CHECK(validation_state IN ('user-configured-unvalidated','scientifically-validated')),
 created_at TEXT NOT NULL, PRIMARY KEY(id, revision));
CREATE TABLE IF NOT EXISTS suitability_assessments (
 id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, profile_revision INTEGER NOT NULL,
 site_id TEXT NOT NULL, target_body TEXT NOT NULL CHECK(target_body IN ('Earth','Moon','Mars')),
 status TEXT NOT NULL CHECK(status IN ('eligible','ineligible','indeterminate')),
 input_snapshot_json TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(profile_id, profile_revision) REFERENCES mission_profiles(id, revision));
CREATE INDEX IF NOT EXISTS idx_mission_profiles_name ON mission_profiles(name);
CREATE INDEX IF NOT EXISTS idx_suitability_created ON suitability_assessments(created_at);
CREATE TABLE IF NOT EXISTS mission_scenarios (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, target_body TEXT NOT NULL CHECK(target_body IN ('Earth','Moon','Mars')),
 site_id TEXT NOT NULL, suitability_assessment_id TEXT, status TEXT NOT NULL,
 input_snapshot_json TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scenarios_created ON mission_scenarios(created_at);
CREATE TABLE IF NOT EXISTS mission_risk_assessments (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, target_body TEXT NOT NULL CHECK(target_body IN ('Earth','Moon','Mars')),
 site_id TEXT NOT NULL, scenario_id TEXT, input_snapshot_json TEXT NOT NULL,
 result_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_created ON mission_risk_assessments(created_at);
CREATE TABLE IF NOT EXISTS mission_risk_reviews (
 id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL REFERENCES mission_risk_assessments(id),
 risk_id TEXT NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL
 CHECK(decision IN ('acknowledged','action-required','mitigation-verified')),
 rationale TEXT NOT NULL, mitigation_evidence_json TEXT NOT NULL, evidence_snapshot_json TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_risk_reviews_assessment ON mission_risk_reviews(assessment_id,risk_id,created_at);
"""

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def initialize() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Backward-compatible additive migrations for Stage 15 review metadata.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(observations)")}
        for name, declaration in (
            ("review_status", "TEXT NOT NULL DEFAULT 'pending-human-review'"),
            ("reviewed_at", "TEXT"),
            ("reviewer", "TEXT"),
            ("review_reason", "TEXT"),
        ):
            if name not in columns:
                conn.execute(f"ALTER TABLE observations ADD COLUMN {name} {declaration}")

@contextmanager
def transaction():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
