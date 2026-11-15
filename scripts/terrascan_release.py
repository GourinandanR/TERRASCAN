#!/usr/bin/env python3
"""Release gate: structural, syntax and archive safety checks; no science scoring."""
import argparse, ast, hashlib, json, pathlib, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = [
    "backend/app/main.py", "backend/app/auth.py", "backend/app/database.py",
    "src/App.tsx", "src/components/LoginWorkspace.tsx", "src/components/AdminWorkspace.tsx",
    "src/lib/session.ts", "src/services/api.ts",
    "docs/backend/STAGE32_USER_AUTHENTICATION_ROLE_BASED_DASHBOARD.md",
    "docs/backend/STAGE38_FINAL_RELEASE_VALIDATION.md",
]
def audit():
    errors=[]
    for rel in REQUIRED:
        if not (ROOT/rel).is_file(): errors.append(f"missing:{rel}")
    for p in (ROOT/"backend").rglob("*.py"):
        try: ast.parse(p.read_text(encoding="utf-8"))
        except Exception as exc: errors.append(f"python-syntax:{p.relative_to(ROOT)}:{exc}")
    pkg=json.loads((ROOT/"package.json").read_text())
    if pkg.get("version") != "3.8.0": errors.append("package-version-not-3.8.0")
    main=(ROOT/"backend/app/main.py").read_text()
    for token in ("api/auth/login","api/auth/register","TERRASCAN_LOGIN_RATE_LIMIT","X-Content-Type-Options"):
        if token not in main: errors.append(f"missing-security-feature:{token}")
    return errors
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--zip",type=pathlib.Path)
    args=parser.parse_args()
    errors=audit()
    if args.zip:
        if not args.zip.is_file(): errors.append("zip-not-found")
        else:
            with zipfile.ZipFile(args.zip) as zf:
                if zf.testzip(): errors.append("zip-integrity-failed")
                names=set(zf.namelist())
                if any(name.endswith("/.env") or name.endswith(".sqlite3") for name in names):
                    errors.append("sensitive-runtime-file-in-archive")
    print(json.dumps({"status":"passed" if not errors else "failed","checks":"structural-and-syntax","errors":errors},indent=2))
    raise SystemExit(0 if not errors else 1)
if __name__=="__main__": main()
