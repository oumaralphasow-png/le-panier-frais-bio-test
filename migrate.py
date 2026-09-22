import subprocess, sys
cmd=[sys.executable,"-m","alembic","upgrade","head"]
raise SystemExit(subprocess.call(cmd))
