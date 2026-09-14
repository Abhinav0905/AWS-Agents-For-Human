"""Ledger durability for aws mode: the SQLite file lives in S3 between invocations.

A daily tick is a single writer, so pull-run-push is enough for the hackathon. DynamoDB is the
production path (the store interface is already shaped for it); see docs/DEPLOY.md.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from .config import settings
from .store import SQLiteLedgerStore


def _s3_target() -> tuple[str, str] | None:
    uri = os.getenv("POSTSCRIPT_LEDGER_S3", "")
    if not uri.startswith("s3://"):
        return None
    bucket, _, key = uri[5:].partition("/")
    return bucket, key or "postscript/ledger.db"


@contextmanager
def ledger(reset: bool = False):
    """Yield a store; in aws mode pull it from S3 first and push it back afterwards."""
    path = Path(os.getenv("POSTSCRIPT_LEDGER_PATH", str(settings.data_dir / "ledger.db")))
    target = _s3_target()
    if target and not reset:
        import boto3

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            boto3.client("s3").download_file(target[0], target[1], str(path))
        except Exception as exc:  # first run: nothing to pull yet
            if "404" not in str(exc) and "NoSuchKey" not in str(exc) and "Not Found" not in str(exc):
                raise
    store = SQLiteLedgerStore(path, reset=reset)
    try:
        yield store
    finally:
        store.db.commit()
        if target:
            import boto3

            boto3.client("s3").upload_file(str(path), target[0], target[1])
