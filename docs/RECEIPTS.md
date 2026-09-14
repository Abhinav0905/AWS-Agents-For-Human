# Receipts

Every tool call the agent makes, every call the policy blocks, and every answer the executor gives becomes a
receipt. Receipts are append-only and hash-chained; the chain is what the Executor's Accounting PDF is built from.

```json
{
  "receipt_id": "rcp_3f1c9a2b7d",
  "estate_id": "est_alvarez",
  "task_id": "task_harborline_bank",
  "sim_time": "2026-03-10",
  "wall_time": "2026-09-12T18:04:11+00:00",
  "actor": "runner",
  "tool": "submit_notification",
  "args_redacted": {
    "institution_id": "harborline", "account_last4": "4417",
    "documents": [{"doc_type": "death_certificate", "is_original": true, "doc_ref": "death_certificate_orig"},
                  {"doc_type": "letters_testamentary", "is_original": false, "doc_ref": "letters_testamentary_copy"}],
    "includes_original": true, "signature_kind": "none", "letter_text": "To Harborline Bank, ..."
  },
  "result_summary": "case_ref=HAR-6305; status=received; message=Notice received by Harborline Bank.",
  "evidence": ["doc:death_certificate_orig", "doc:letters_testamentary_copy", "gateway:case:HAR-6305"],
  "policy": {"decision": "permit", "policy_id": "approved:D2", "human_approval_id": "dec_fc4e8bd7cf"},
  "prev_hash": "sha256:9f2c...",
  "hash": "sha256:41ab..."
}
```

Rules

- `hash` = SHA-256 of the canonical JSON (sorted keys, no whitespace) of every field except `hash`.
- `prev_hash` of the first receipt is `sha256(genesis:<estate_id>)`.
- `args_redacted` is what the tool received after redaction: account-number-like strings keep their last four
  digits, SSN patterns are replaced, keys named ssn / pin / password / token are dropped.
- Blocked calls are receipts with `policy.decision = "forbid"` and `policy_id = "gate:D1"` (or whichever types).
- Human answers are receipts with `actor = "executor:<id>"`, `tool = "inbox.approve|deny|edit"`.
- `policy.human_approval_id` on a permitted gated call names the decision the executor made.
- The store exposes no UPDATE or DELETE on the receipts table. `postscript verify-chain` walks the chain and
  reports the first broken link, if any.

The PDF (`postscript accounting`) has a cover with the genesis and head hashes and the verification result, a
summary, the decisions with who answered and when, the originals consumed, open items, and the full schedule of
actions, one row per receipt.
