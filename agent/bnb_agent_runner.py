from __future__ import annotations

from agent.skill_runner import analyze_payload


class BnbAgentSkillWrapper:
    """Thin adapter kept separate from the core Track 2 strategy logic."""

    name = "cmc_style_strategy_skill"
    description = "Backtestable crypto strategy Skill; no transaction signing."

    def run(self, payload: dict) -> dict:
        return analyze_payload(payload)


def run_bnb_agent_demo(payload: dict) -> dict:
    return BnbAgentSkillWrapper().run(payload)

