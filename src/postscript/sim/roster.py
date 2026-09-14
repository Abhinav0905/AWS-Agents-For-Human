"""Single source of truth for the synthetic Alvarez estate.

The dataset generator, the simulator and the metrics all read from here, so the
documents, the institution behaviour and the expected decisions can never drift apart.
Everything below is fictional.
"""

from __future__ import annotations

ESTATE = {
    "id": "est_alvarez",
    "decedent_name": "Robert (Bob) Alvarez",
    "date_of_death": "2026-03-02",
    "executor_name": "Maya Alvarez",
    "executor_id": "maya",
    "heirs": ["Maya Alvarez", "Daniel Alvarez"],
    "certified_copies_on_hand": 5,
}

SIM_START = "2026-03-09"

# script keys are implemented in world.py
ROSTER: list[dict] = [
    {
        "id": "harborline", "name": "Harborline Bank", "kind": "bank", "channel": "mail",
        "requirements": [
            {"doc_type": "death_certificate", "original_required": True, "notes": "certified copy, no photocopies"},
            {"doc_type": "letters_testamentary", "original_required": False, "notes": "court-issued"},
        ],
        "signature_kind": "none", "response_days": 5, "script": "bank_close",
        "accounts": [{"label": "Checking", "last4": "4417"}, {"label": "Savings", "last4": "9902"}],
        "initial_task": "notify",
        "decision_events": [["D2"], ["D4"]],
        "documents": [
            {"type": "statement", "title": "Monthly statement", "render": "pdf", "account": "4417",
             "lines": ["Statement period: Feb 1 - Feb 28, 2026", "Ending balance: $18,204.55",
                       "Estate services: mail certified documents to PO Box 1180, Oakland CA 94604"]},
            {"type": "statement", "title": "Monthly statement", "render": "png", "account": "9902",
             "lines": ["Statement period: Feb 1 - Feb 28, 2026", "Ending balance: $42,910.02",
                       "Estate services: mail certified documents to PO Box 1180, Oakland CA 94604"]},
            {"type": "statement", "title": "Monthly statement (duplicate mailing)", "render": "pdf", "account": "4417",
             "lines": ["Statement period: Feb 1 - Feb 28, 2026", "Ending balance: $18,204.55",
                       "Estate services: mail certified documents to PO Box 1180, Oakland CA 94604"]},
        ],
    },
    {
        "id": "pacific_power", "name": "Pacific Coast Power", "kind": "utility", "channel": "portal",
        "requirements": [{"doc_type": "death_certificate", "original_required": False, "notes": "upload a copy"}],
        "signature_kind": "none", "response_days": 2, "script": "utility_bill", "final_bill": 142.17,
        "accounts": [{"label": "Electric and gas service, 1420 Alder St", "last4": "3381"}],
        "initial_task": "notify",
        "decision_events": [["D1"]],
        "documents": [
            {"type": "bill", "title": "Energy statement", "render": "pdf", "account": "3381",
             "lines": ["Service address: 1420 Alder St, Oakland CA", "Amount due: $142.17 by Mar 28, 2026",
                       "Report a death or transfer service at pacificcoastpower.example/estates"]},
        ],
    },
    {
        "id": "northwind", "name": "Northwind Telecom", "kind": "telecom", "channel": "email",
        "requirements": [{"doc_type": "death_certificate", "original_required": False, "notes": "copy by email"}],
        "signature_kind": "none", "response_days": 3, "script": "telecom_ignore", "form_type": "authorized_rep_form",
        "accounts": [{"label": "Mobile and home internet", "last4": "7720"}],
        "initial_task": "notify",
        "decision_events": [],
        "documents": [
            {"type": "bill", "title": "Your Northwind bill is ready", "render": "eml", "account": "7720",
             "lines": ["Monthly total: $96.40", "Bereavement requests: estates@northwind.example"]},
        ],
    },
    {
        "id": "sequoia_life", "name": "Sequoia Life Insurance", "kind": "insurer", "channel": "mail",
        "requirements": [{"doc_type": "death_certificate", "original_required": False, "notes": "copy to open the claim"}],
        "signature_kind": "none", "response_days": 4, "script": "insurer_claim", "election_options": ["lump_sum", "annuity"],
        "accounts": [{"label": "Term life policy, beneficiary Maya Alvarez", "last4": "5518"}],
        "initial_task": "claim",
        "decision_events": [["D2"], ["D4"]],
        "documents": [
            {"type": "policy_letter", "title": "Annual policy summary", "render": "pdf", "account": "5518",
             "lines": ["Face amount: $250,000", "Primary beneficiary: Maya Alvarez",
                       "Claims: Sequoia Life Claims, PO Box 400, Sacramento CA 95812"]},
        ],
    },
    {
        "id": "golden_pension", "name": "Golden State Pension Board", "kind": "pension", "channel": "mail",
        "requirements": [{"doc_type": "death_certificate", "original_required": False, "notes": "copy accepted"}],
        "signature_kind": "none", "response_days": 5, "script": "pension_notary", "form_type": "survivor_form",
        "accounts": [{"label": "Retirement benefit, member", "last4": "0064"}],
        "initial_task": "notify",
        "decision_events": [["D3"]],
        "documents": [
            {"type": "benefit_letter", "title": "Benefit payment notice", "render": "png", "account": "0064",
             "lines": ["Monthly benefit: $2,140.00", "Survivor benefits require a notarized survivor form",
                       "Member services: 1-800-555-0164"]},
            {"type": "benefit_letter", "title": "Benefit payment notice", "render": "pdf", "account": "0064",
             "lines": ["Monthly benefit: $2,140.00", "Survivor benefits require a notarized survivor form",
                       "Member services: 1-800-555-0164"]},
        ],
    },
    {
        "id": "streambox", "name": "StreamBox", "kind": "subscription", "channel": "email",
        "requirements": [{"doc_type": "death_certificate", "original_required": False, "notes": "copy optional"}],
        "signature_kind": "none", "response_days": 1, "script": "subscription_cancel",
        "accounts": [{"label": "Premium plan", "last4": "2210"}],
        "initial_task": "cancel",
        "decision_events": [],
        "documents": [
            {"type": "receipt", "title": "Your StreamBox receipt", "render": "eml", "account": "2210",
             "lines": ["Premium plan: $17.99 charged Mar 1, 2026", "Manage or cancel at streambox.example/account"]},
        ],
    },
    {
        "id": "equinox_bureau", "name": "Equinox Credit Bureau", "kind": "credit_bureau", "channel": "mail",
        "requirements": [{"doc_type": "death_certificate", "original_required": False, "notes": "copy by mail"}],
        "signature_kind": "none", "response_days": 14, "script": "credit_bureau_alert",
        "accounts": [{"label": "Credit file", "last4": "8891"}],
        "initial_task": "notify",
        "decision_events": [],
        "documents": [
            {"type": "notice", "title": "Annual credit file summary", "render": "pdf", "account": "8891",
             "lines": ["Open tradelines: 3", "Deceased alerts: mail a copy of the death certificate to PO Box 9",
                       "Equinox Credit Bureau, Allen TX 75013"]},
        ],
    },
    {
        "id": "state_dmv", "name": "State Department of Motor Vehicles", "kind": "dmv", "channel": "in_person",
        "requirements": [
            {"doc_type": "death_certificate", "original_required": False, "notes": "copy"},
            {"doc_type": "title", "original_required": False, "notes": "vehicle title, signed by executor"},
        ],
        "signature_kind": "wet", "response_days": 20, "script": "dmv_title",
        "accounts": [{"label": "2019 Subaru Outback, plate 8ABC123", "last4": "6142"}],
        "initial_task": "transfer",
        "decision_events": [["D3"], ["D5"]],
        "documents": [
            {"type": "registration", "title": "Vehicle registration renewal notice", "render": "pdf", "account": "6142",
             "lines": ["Vehicle: 2019 Subaru Outback", "Renewal due: Apr 15, 2026, $218",
                       "Title transfers require an in-person appointment"]},
        ],
    },
    {
        "id": "summit_brokerage", "name": "Summit Brokerage", "kind": "brokerage", "channel": "mail",
        "requirements": [
            {"doc_type": "death_certificate", "original_required": True, "notes": "certified original"},
            {"doc_type": "transfer_form", "original_required": False, "notes": "medallion signature guarantee"},
        ],
        "signature_kind": "medallion", "response_days": 6, "script": "brokerage_medallion",
        "accounts": [{"label": "Individual brokerage account", "last4": "7305"}],
        "initial_task": "transfer",
        "decision_events": [["D2", "D3"]],
        "documents": [
            {"type": "statement", "title": "Quarterly statement", "render": "pdf", "account": "7305",
             "lines": ["Portfolio value: $96,330.18", "Estate transfers need a medallion signature guarantee",
                       "Summit Brokerage Estate Desk, PO Box 2200, Denver CO 80201"]},
        ],
    },
    {
        "id": "redwood_fitness", "name": "Redwood Fitness", "kind": "gym", "channel": "mail",
        "requirements": [{"doc_type": "death_certificate", "original_required": False, "notes": "copy by mail"}],
        "signature_kind": "none", "response_days": 3, "script": "gym_stonewall",
        "accounts": [{"label": "Monthly membership", "last4": "1177"}],
        "initial_task": "cancel",
        "decision_events": [],
        "documents": [
            {"type": "billing_notice", "title": "Membership billing notice", "render": "png", "account": "1177",
             "lines": ["Monthly dues: $54.00", "Cancellations must be sent in writing to 900 Broadway, Oakland CA"]},
            {"type": "billing_notice", "title": "Membership billing notice", "render": "pdf", "account": "1177",
             "lines": ["Monthly dues: $54.00", "Cancellations must be sent in writing to 900 Broadway, Oakland CA"]},
        ],
    },
]

DISTRACTORS = [
    {"type": "flyer", "title": "Tony's Pizza: two large pies for $24", "render": "pdf",
     "lines": ["Free delivery in Oakland", "Order at tonys.example"]},
]

# Inbound messages the world delivers on specific sim days (day 0 = SIM_START).
INBOUND: list[dict] = [
    {"day": 18, "from": "Daniel Alvarez", "kind": "heir", "institution_id": "state_dmv",
     "institution_name": "State Department of Motor Vehicles", "action": "object",
     "subject": "About Dad's car",
     "body": "Maya, I do not want to sell the Outback. Please hold off on the title transfer until we talk."},
    {"day": 21, "from": "Daniel Alvarez", "kind": "heir", "institution_id": "state_dmv",
     "institution_name": "State Department of Motor Vehicles", "action": "agree",
     "subject": "Re: About Dad's car",
     "body": "Talked it through. Go ahead and sell it, split the proceeds as the will says."},
]


def institution(inst_id: str) -> dict:
    for r in ROSTER:
        if r["id"] == inst_id:
            return r
    raise KeyError(inst_id)


def ground_truth() -> dict:
    events = []
    for r in ROSTER:
        for types in r["decision_events"]:
            events.append({"institution_id": r["id"], "types": types})
    return {
        "estate": ESTATE,
        "sim_start": SIM_START,
        "institutions": [
            {"id": r["id"], "name": r["name"], "kind": r["kind"], "channel": r["channel"],
             "accounts": [a["last4"] for a in r["accounts"]], "script": r["script"]}
            for r in ROSTER
        ],
        "decision_events": events,
        "expected_certificates_remaining": ESTATE["certified_copies_on_hand"]
        - sum(1 for r in ROSTER for t in r["decision_events"] if "D2" in t),
    }
