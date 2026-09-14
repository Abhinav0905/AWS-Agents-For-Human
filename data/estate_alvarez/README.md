# Synthetic estate: Robert (Bob) Alvarez

Everything in this folder is invented for the Postscript demo. The institutions do not exist, the people do not exist, and no document contains a Social Security number or a full account number.

- `mail/` is the shoebox: statements, bills, notices and emails as PDFs, PNG 'scans' and .eml files. File names carry no hints. One item is a flyer; one statement is a duplicate mailing.
- `inbound/` holds messages the simulator delivers on specific simulated days (an heir objecting, then agreeing).
- `ground_truth.json` lists the institutions, the mail manifest, and the decision events an executor would have to make. The metrics score the agent against it.

Regenerate with `python scripts/make_dataset.py`.
