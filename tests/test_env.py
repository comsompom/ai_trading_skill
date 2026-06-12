from __future__ import annotations

import os

from app.env import load_env_file


def test_load_env_file_sets_missing_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# comment",
                "PLAIN_VALUE=abc",
                "QUOTED_VALUE=\"quoted abc\"",
                "export EXPORTED_VALUE=from-export",
                "INLINE_COMMENT=value # local note",
            ]
        ),
        encoding="utf-8",
    )
    for key in ["PLAIN_VALUE", "QUOTED_VALUE", "EXPORTED_VALUE", "INLINE_COMMENT"]:
        monkeypatch.delenv(key, raising=False)

    load_env_file(env_file)

    assert os.environ["PLAIN_VALUE"] == "abc"
    assert os.environ["QUOTED_VALUE"] == "quoted abc"
    assert os.environ["EXPORTED_VALUE"] == "from-export"
    assert os.environ["INLINE_COMMENT"] == "value"


def test_load_env_file_does_not_override_existing_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_VALUE=from-file", encoding="utf-8")
    monkeypatch.setenv("EXISTING_VALUE", "from-env")

    load_env_file(env_file)

    assert os.environ["EXISTING_VALUE"] == "from-env"
