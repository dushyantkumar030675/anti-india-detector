import sys
import importlib.util
from pathlib import Path

backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

spec = importlib.util.spec_from_file_location(
    "backend_api_main",
    backend_path / "api" / "main.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

app = module.app
