"""Runtime settings, read once from the environment."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    mode: str = "local"  # local | aws
    model: str = "scripted"  # scripted | bedrock
    model_id: str | None = None
    region: str = "us-west-2"
    data_dir: Path = Path(".postscript")
    estate_dir: Path = Path("data/estate_alvarez")
    seed: int = 7
    notify: str = "none"  # none | sns
    sns_topic_arn: str | None = None
    sim_start: str = "2026-03-09"  # one week after the date of death in the synthetic estate

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            mode=os.getenv("POSTSCRIPT_MODE", "local"),
            model=os.getenv("POSTSCRIPT_MODEL", "scripted"),
            model_id=os.getenv("POSTSCRIPT_MODEL_ID") or None,
            region=os.getenv("AWS_REGION", "us-west-2"),
            data_dir=Path(os.getenv("POSTSCRIPT_DATA_DIR", ".postscript")),
            estate_dir=Path(os.getenv("POSTSCRIPT_ESTATE_DIR", "data/estate_alvarez")),
            seed=int(os.getenv("POSTSCRIPT_SIM_SEED", "7")),
            notify=os.getenv("POSTSCRIPT_NOTIFY", "none"),
            sns_topic_arn=os.getenv("POSTSCRIPT_SNS_TOPIC_ARN") or None,
        )


settings = Settings.from_env()
