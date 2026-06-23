from __future__ import annotations

import os

from mcbench.config import load_repo_env


def test_load_repo_env_reads_dotenv_without_overwriting_existing_vars(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "# comment",
                "OPENAI_API_KEY=test-key",
                "MCBENCH_PROMPT_MODEL=\"gpt-test\"",
                "export MCBENCH_PROMPT_TIMEOUT_SECONDS=11",
            ]
        )
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MCBENCH_PROMPT_MODEL", "existing-model")
    monkeypatch.delenv("MCBENCH_PROMPT_TIMEOUT_SECONDS", raising=False)

    load_repo_env(tmp_path)

    assert os.environ["OPENAI_API_KEY"] == "test-key"
    assert os.environ["MCBENCH_PROMPT_MODEL"] == "existing-model"
    assert os.environ["MCBENCH_PROMPT_TIMEOUT_SECONDS"] == "11"
