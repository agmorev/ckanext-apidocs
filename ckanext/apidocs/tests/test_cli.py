"""Tests for the apidocs CLI."""

import json

from ckanext.apidocs import cli as apidocs_cli


def test_export_to_stdout(cli):
    """Calling `apidocs export` with no args writes YAML to stdout."""
    # use default (yaml) and stdout
    result = cli.invoke(apidocs_cli.apidocs, ["export"])
    assert not result.exit_code, result.output
    assert "openapi" in result.output
    assert "/api/3/action/package_show" in result.output
    assert "Authorization" in result.output


def test_export_to_file_json(tmp_path, cli):
    out = tmp_path / "spec.json"
    result = cli.invoke(apidocs_cli.apidocs, ["export", str(out), "--format=json"])
    assert not result.exit_code, result.output
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["openapi"] == "3.0.0"
    assert "/api/3/action/package_show" in json.dumps(data)
