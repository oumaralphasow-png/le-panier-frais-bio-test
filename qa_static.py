from pathlib import Path
import re, sys

BASE=Path(__file__).resolve().parent
app=(BASE/"app.py").read_text(encoding="utf-8")
html=(BASE/"index.html").read_text(encoding="utf-8")
issues=[]

def check(ok, msg):
    if not ok: issues.append(msg)

check('version="1.0.0"' in app, "API version is not 1.0.0")
check('"version":"1.0.0"' in app, "Health endpoint is not 1.0.0")
check("SEED_DEMO_DATA" in app, "Demo-data switch missing")
check("BOOTSTRAP_ADMIN_EMAIL" in app, "Bootstrap admin support missing")
check("lpfb55" not in html, "Legacy localStorage key lpfb55 still present")
check("lpfb63" in html, "Current localStorage key lpfb63 missing")
for token in ["admin@lpfb.test","pro@example.test","client@example.test","LPFB-Test-2026!","LPFB-Pro-2026!","LPFB-Client-2026!"]:
    check(token not in html, f"Demo credential leaked in static HTML: {token}")
check('@app.get("/preproduction/readiness")' in app, "Preproduction readiness endpoint missing")
check("LPFB_BACKUP_1_0_0" in app, "V97 backup schema marker missing")
check('@app.post("/public/general-sourcing-request")' in app, "General sourcing route missing")
check('@app.get("/ops/integrity")' in app, "Integrity route missing")
check('@app.get("/ops/release-status")' in app, "Release status route missing")

routes=re.findall(r'@app\.(get|post|put|delete)\("([^"]+)"\)',app)
seen=set()
for route in routes:
    check(route not in seen, f"Duplicate route: {route[0].upper()} {route[1]}")
    seen.add(route)

# Sensitive internal reads should be staff-gated; dedicated B2C/PRO/auth routes are excluded.
defs=re.findall(r'@app\.(get|post|put|delete)\("([^"]+)"\)\ndef ([^(]+)\((.*?)\):',app,re.S)
for method,path,name,args in defs:
    if "Depends(current_user)" in args and not (path.startswith("/b2c") or path.startswith("/pro") or path.startswith("/auth")):
        issues.append(f"Generic authenticated route still not role-gated: {method.upper()} {path}")

if issues:
    print("LPFB 1.0.0 STATIC QA: FAIL")
    for x in issues: print(" -",x)
    sys.exit(1)

print("LPFB 1.0.0 STATIC QA: PASS")
print(f"Routes checked: {len(routes)}")
print("Demo data can be disabled for production.")
print("Production bootstrap admin support present.")


check("class LotStageInfo(Base)" in app, "LotStageInfo model missing")
check('@app.get("/stock/stages")' in app, "Stock stage endpoint missing")
check('set_lot_stage(db,output.id,"PREPARED","PRODUCTION_OUTPUT")' in app, "Production output stage assignment missing")

check("def fulfill_order_reservations" in app, "Reservation fulfillment helper missing")
check("def cancel_order_resources" in app, "Order cancellation lifecycle helper missing")
check('@app.get("/orders/{order_id}/allocations")' in app, "Order allocations endpoint missing")

check((BASE/"alembic.ini").exists(), "alembic.ini missing")
check((BASE/"alembic/env.py").exists(), "Alembic env.py missing")
check((BASE/"alembic/versions/v100_baseline.py").exists(), "V100 baseline migration missing")
check('@app.get("/ops/schema-status")' in app, "Schema status endpoint missing")
check('AUTO_CREATE_SCHEMA' in app, "AUTO_CREATE_SCHEMA guard missing")

render_prod=(BASE/"render.production.yaml").read_text(encoding="utf-8")
check("https://lepanierfraisbio.fr" in render_prod, "Production canonical domain missing")
check("YOUR-PRODUCTION-DOMAIN.example" not in render_prod, "Production domain placeholder remains")

render_prod=(BASE/"render.production.yaml").read_text(encoding="utf-8")
check("oumar.alpha.sow@hotmail.fr" in render_prod, "Final production admin email missing")
check("value: production" in render_prod, "Release channel is not production")

check("FINAL-STABLE" in (BASE/"release_manifest.json").read_text(encoding="utf-8"), "Final stable manifest marker missing")
for token in ["admin@lpfb.test","pro@example.test","client@example.test","LPFB-Test-2026!","LPFB-Pro-2026!","LPFB-Client-2026!"]:
    check(token not in app, f"Hardcoded demo credential remains in backend: {token}")
