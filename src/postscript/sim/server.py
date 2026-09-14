"""institution-gateway: the simulator exposed over MCP (stdio by default, streamable HTTP with --http)."""

from __future__ import annotations

import os
import sys

try:  # mcp >= 2 renamed FastMCP to MCPServer; keep working on either
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore[no-redef]

from .world import World

mcp = _Server("institution-gateway")
_world = World(seed=int(os.getenv("POSTSCRIPT_SIM_SEED", "7")), start=os.getenv("POSTSCRIPT_SIM_START", "2026-03-09"))

HARNESS_TOOLS = {"advance_clock", "reset_world", "world_snapshot"}


@mcp.tool()
def list_institutions() -> list[dict]:
    """List the institutions this gateway can reach (id, name, kind, contact channel)."""
    return _world.list_institutions()


@mcp.tool()
def get_requirements(institution_id: str) -> dict:
    """Public 'report a death' requirements for one institution: documents, whether originals are required,
    signature kind, whether an in-person visit is needed, and the expected response time in days."""
    return _world.get_requirements(institution_id)


@mcp.tool()
def submit_notification(institution_id: str, account_last4: str, letter_text: str, documents: list[dict],
                        includes_original: bool, signature_kind: str) -> dict:
    """Send the death notification packet to an institution. documents is a list of
    {doc_type, is_original, doc_ref}. includes_original must be true if any document is an original certified
    copy (originals are consumed). signature_kind is one of none|wet|notarized|medallion. Returns a case_ref."""
    return _world.submit_notification(institution_id, account_last4, letter_text, documents, includes_original,
                                      signature_kind)


@mcp.tool()
def check_status(case_ref: str) -> dict:
    """Current status of an open case: status, message, requested_items, amount_due, closing_offer, options."""
    return _world.check_status(case_ref)


@mcp.tool()
def send_follow_up(case_ref: str, text: str, certified: bool) -> dict:
    """Send a follow-up on a case. certified=true sends it by certified mail (use after two non-responses)."""
    return _world.send_follow_up(case_ref, text, certified)


@mcp.tool()
def submit_document(case_ref: str, doc_type: str, includes_original: bool, signature_kind: str) -> dict:
    """Send one additional document on an open case. includes_original=true consumes an original certified copy.
    signature_kind is none|wet|notarized|medallion."""
    return _world.submit_document(case_ref, doc_type, includes_original, signature_kind)


@mcp.tool()
def pay(case_ref: str, amount_cents: int, method: str = "estate_account") -> dict:
    """Pay an amount due on a case from the estate account, in whole cents (14217 means $142.17).
    Money leaves the estate."""
    return _world.pay(case_ref, amount_cents, method)


@mcp.tool()
def close_account(case_ref: str) -> dict:
    """Accept a closing offer and close the account(s) on a case. Irreversible."""
    return _world.close_account(case_ref)


@mcp.tool()
def elect_option(case_ref: str, option: str) -> dict:
    """Record an election (for example a payout option) on a case. Irreversible."""
    return _world.elect_option(case_ref, option)


@mcp.tool()
def get_inbox() -> list[dict]:
    """Inbound messages since the last call: institution replies and emails from heirs."""
    return _world.get_inbox()


# --- harness-only tools; the runner never sees these (filtered by name) ---------------------
@mcp.tool()
def advance_clock(days: int = 1) -> dict:
    """HARNESS ONLY. Advance the simulated clock and fire scheduled institution events."""
    return _world.advance(days)


@mcp.tool()
def reset_world(seed: int = 7, start: str = "2026-03-09") -> dict:
    """HARNESS ONLY. Reset the world."""
    global _world
    _world = World(seed=seed, start=start)
    return {"ok": True, "sim_date": _world.sim_date()}


@mcp.tool()
def world_snapshot() -> dict:
    """HARNESS ONLY. Full world state for metrics."""
    return _world.snapshot()


def main() -> None:
    if "--http" in sys.argv:
        host, port = os.getenv("HOST", "0.0.0.0"), int(os.getenv("PORT", "8080"))
        try:
            mcp.run(transport="streamable-http", host=host, port=port)
        except TypeError:  # mcp 1.x FastMCP takes settings instead of kwargs
            mcp.settings.host, mcp.settings.port = host, port  # type: ignore[attr-defined]
            mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
