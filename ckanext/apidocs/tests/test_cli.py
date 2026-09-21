"""Tests for the apidocs CLI."""

from __future__ import annotations

import json

from ckanext.apidocs import cli as apidocs_cli


def test_export_writes_yaml_to_stdout(cli):
    result = cli.invoke(apidocs_cli.apidocs, ["export"])

    assert not result.exit_code, result.output
    assert "openapi:" in result.output
    assert "/package_show:" in result.output
    assert "Authorization" in result.output


def test_export_writes_json_to_a_file(cli, tmp_path):
    target = tmp_path / "spec.json"

    result = cli.invoke(
        apidocs_cli.apidocs, ["export", str(target), "--format=json"]
    )

    assert not result.exit_code, result.output

    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload["openapi"] == "3.0.0"
    assert "/package_show" in payload["paths"]
    assert str(target) in result.output


def test_export_accepts_overrides(cli):
    result = cli.invoke(
        apidocs_cli.apidocs,
        [
            "export",
            "--format=json",
            "--base-path=/api/4/action",
            "--version=9.9.9",
        ],
    )

    assert not result.exit_code, result.output

    payload = json.loads(result.output)

    assert payload["servers"] == [{"url": "/api/4/action"}]
    assert payload["info"]["version"] == "9.9.9"


def test_export_reports_unwritable_target(cli, tmp_path):
    target = tmp_path / "missing" / "spec.json"

    result = cli.invoke(apidocs_cli.apidocs, ["export", str(target)])

    assert result.exit_code != 0
    assert "Could not write the specification" in result.output


def test_commands_do_not_include_example_group():
    assert [command.name for command in apidocs_cli.get_commands()] == ["apidocs"]
