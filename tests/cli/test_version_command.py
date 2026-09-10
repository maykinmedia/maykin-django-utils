from typer.testing import CliRunner

from maykin_common.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "v0.21.0" in result.output
