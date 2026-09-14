"""Playbooks: what an executor usually has to do per kind of institution, and the letters to send."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

PLAYBOOK_DIR = Path(__file__).resolve().parents[2] / "playbooks"


class Playbook(BaseModel):
    kind: str
    summary: str
    documents: list[str]
    originals_typical: bool = False
    channel: str = "mail"
    typical_response_days: int = 7
    initial_task: str = "notify"
    likely_flags: dict[str, bool] = Field(default_factory=dict)
    escalation_days: list[int] = Field(default_factory=lambda: [7, 14, 21])
    letter: str


_cache: dict[str, Playbook] = {}


def load(kind: str) -> Playbook:
    if kind not in _cache:
        path = PLAYBOOK_DIR / f"{kind}.yaml"
        if not path.exists():
            path = PLAYBOOK_DIR / "other.yaml"
        _cache[kind] = Playbook.model_validate(yaml.safe_load(path.read_text()))
    return _cache[kind]


def render_letter(kind: str, institution_name: str, account_last4: str, decedent_name: str, executor_name: str,
                  date_of_death: str) -> str:
    pb = load(kind)
    return pb.letter.format(institution=institution_name, last4=account_last4, decedent=decedent_name,
                            executor=executor_name, dod=date_of_death).strip()
