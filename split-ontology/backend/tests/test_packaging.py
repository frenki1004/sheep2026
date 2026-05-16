import os
import subprocess
import sys
import tempfile


def test_installed_package_imports_outside_project_pythonpath():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as cwd:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import split_ontology.api; print(split_ontology.api.app.title)",
            ],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr
    assert "Split Building Ontology MVP" in result.stdout
