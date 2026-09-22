from pathlib import Path
import sys, json

BASE=Path(__file__).resolve().parent
issues=[]
warnings=[]

def fail(msg): issues.append(msg)
def warn(msg): warnings.append(msg)

app=(BASE/"app.py").read_text(encoding="utf-8")
render=(BASE/"render.production.yaml").read_text(encoding="utf-8")
docker=(BASE/"Dockerfile").read_text(encoding="utf-8")
html=(BASE/"index.html").read_text(encoding="utf-8")
readme=(BASE/"README.md").read_text(encoding="utf-8")

demo_literals=["admin@lpfb.test","pro@example.test","client@example.test",
               "LPFB-Test-2026!","LPFB-Pro-2026!","LPFB-Client-2026!"]
for secret in demo_literals:
    if secret in html: fail(f"Identifiant de démonstration exposé dans index.html: {secret}")
    if secret in app: fail(f"Identifiant de démonstration codé en dur dans app.py: {secret}")

if "YOUR-PRODUCTION-DOMAIN.example" in render: fail("Domaine exemple encore présent.")
if "admin@YOUR-DOMAIN.example" in render: fail("E-mail administrateur exemple encore présent.")
if "https://lepanierfraisbio.fr" not in render: fail("Domaine canonique absent.")
if "https://www.lepanierfraisbio.fr" not in render: fail("Origine www absente.")
if "oumar.alpha.sow@hotmail.fr" not in render: fail("E-mail administrateur absent.")

if 'SEED_DEMO_DATA\n        value: "false"' not in render: fail("SEED_DEMO_DATA=false absent.")
if 'PRODUCTION_STRICT\n        value: "true"' not in render: fail("PRODUCTION_STRICT=true absent.")
if 'key: AUTO_CREATE_SCHEMA' not in render or 'value: "false"' not in render: fail("AUTO_CREATE_SCHEMA=false absent.")
if "preDeployCommand: python -m alembic upgrade head" not in render: fail("Migration Alembic pré-déploiement absente.")
if "healthCheckPath: /health/ready" not in render: fail("Health check /health/ready absent.")
if 'key: RELEASE_CHANNEL' not in render or 'value: stable' not in render: fail("RELEASE_CHANNEL=stable absent.")

if 'version="1.0.0"' not in app: fail("Version API 1.0.0 introuvable.")
if "LPFB_BACKUP_1_0_0" not in app: fail("Marqueur backup 1.0.0 absent.")
for endpoint in ['/health/ready','/ops/integrity','/ops/release-status','/ops/schema-status']:
    if endpoint not in app: fail(f"Endpoint requis absent: {endpoint}")

if not (BASE/"alembic.ini").exists(): fail("alembic.ini absent.")
if not (BASE/"alembic/env.py").exists(): fail("alembic/env.py absent.")
if not (BASE/"alembic/versions/v100_baseline.py").exists(): fail("Migration baseline absente.")
if not (BASE/"FINAL_ACCEPTANCE.md").exists(): fail("FINAL_ACCEPTANCE.md absent.")
if "HEALTHCHECK" not in docker: warn("Dockerfile sans HEALTHCHECK.")

result={"status":"PASS" if not issues else "FAIL","blocking":issues,"warnings":warnings}
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(1 if issues else 0)
