"""Generate contracts from the real default application, or verify with --check."""
import sys
from pathlib import Path
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import create_app
from app.config import Settings
from app.connectors.base import ConnectorHealth
from app.normalization.models import NormalizedEvent
from app.schemas import IncidentOut

root=Path(__file__).resolve().parents[1]
app=create_app(Settings(app_env="development",allow_fixtures=False,enable_legacy_mock_routes=False,_env_file=None))
artifacts={root/"docs/openapi.json":app.openapi()}
for name,model in {"normalized-event":NormalizedEvent,"incident":IncidentOut,"connector-health":ConnectorHealth}.items():
    artifacts[root/f"contracts/{name}.schema.json"]=model.model_json_schema()
check="--check" in sys.argv
for path,data in artifacts.items():
    content=json.dumps(data,indent=2,ensure_ascii=False)+"\n"
    if check:
        if not path.exists() or json.loads(path.read_text())!=data:
            raise SystemExit(f"Contract differs from runtime: {path.relative_to(root)}")
    else:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
print("contracts match runtime" if check else "contracts regenerated")
