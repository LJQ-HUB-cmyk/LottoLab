import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_deployed_entrypoint_loads_uninstalled_backend_from_another_directory(tmp_path):
    root = Path(__file__).resolve().parents[1]
    deployment = tmp_path / "deployment"
    shutil.copytree(
        root / "backend/lottolab",
        deployment / "backend/lottolab",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copy2(root / "app.py", deployment / "app.py")
    frontend = deployment / "frontend/dist"
    frontend.mkdir(parents=True)
    (frontend / "index.html").write_text("<h1>Isolated LottoLab</h1>", encoding="utf-8")
    code = """
import importlib.util
import sys
from pathlib import Path

original, deployed = map(Path, sys.argv[1:])
sys.path[:] = [p for p in sys.path if Path(p).resolve() not in {original, original / 'backend'}]
assert importlib.util.find_spec('lottolab') is None, 'Must not use the local editable install'
spec = importlib.util.spec_from_file_location('cloud_entrypoint', deployed / 'app.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from fastapi.testclient import TestClient
with TestClient(module.app, base_url='https://preview.example') as client:
    assert client.get('/').text == '<h1>Isolated LottoLab</h1>'
    assert client.get('/api/v1/rules').status_code == 200
    assert module.app.state.settings.public_mode is True
    assert module.app.state.settings.require_read_auth is False
    assert module.app.state.settings.execution_mode == 'request'
print('isolated deployment startup PASS')
"""
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("LOTTOLAB_", "VERCEL_"))}
    environment.update(
        LOTTOLAB_DATABASE_URL="postgresql://fixture:fixture-password@db.example/lottolab",
        LOTTOLAB_ADMIN_TOKEN="isolated-entrypoint-test-token-32-characters",
        VERCEL_URL="preview.example",
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(root), str(deployment)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "startup PASS" in result.stdout


def test_calculation_does_not_reimport_the_hosting_runtime_main(tmp_path):
    runtime = tmp_path / "host_runtime.py"
    runtime.write_text(
        """
if __name__ != '__main__':
    raise RuntimeError('A hosting runtime must not be started again by a calculation')

from pathlib import Path
from lottolab.config import Settings
from lottolab.db import Base, Job, make_engine, make_session_factory
from lottolab.worker import run_request_job

settings = Settings(_env_file=None, database_url='sqlite:///runtime-test.db',
                    data_dir=Path('.'), execution_mode='request', job_timeout_seconds=10)
engine = make_engine(settings.database_url)
Base.metadata.create_all(engine)
factory = make_session_factory(engine)
with factory() as db:
    job = Job(kind='simulation', lottery='ssq', dataset_kind='real',
              params={'lottery': 'ssq', 'iterations': 1000})
    db.add(job)
    db.commit()
    job_id = job.id
run_request_job(factory, job_id, settings)
with factory() as db:
    job = db.get(Job, job_id)
    assert job.status == 'completed', job.error
    assert job.result['iterations'] == 1000
    assert job.result['execution']['code_fingerprint']
engine.dispose()
print('hosted calculation PASS')
""",
        encoding="utf-8",
    )
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("LOTTOLAB_", "VERCEL_"))}
    result = subprocess.run(
        [sys.executable, str(runtime)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "hosted calculation PASS" in result.stdout


def test_execution_records_source_version_without_an_installed_distribution(monkeypatch):
    from importlib import metadata

    from lottolab import __version__
    from lottolab.provenance import execution_metadata

    original_version = metadata.version

    def installed_version(name):
        if name == "lottolab":
            raise metadata.PackageNotFoundError(name)
        return original_version(name)

    monkeypatch.setattr(metadata, "version", installed_version)
    result = execution_metadata("test-rule")
    assert result["packages"]["lottolab"] == __version__
    assert result["packages"]["numpy"] == original_version("numpy")
    assert result["rule_version"] == "test-rule"
