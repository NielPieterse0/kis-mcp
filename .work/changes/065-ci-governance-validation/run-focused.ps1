$ErrorActionPreference = 'Stop'
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:UV_OFFLINE = '1'
uv run --offline --no-sync pytest -q tests/test_change_governance.py tests/work_management/test_ci_workflow.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
