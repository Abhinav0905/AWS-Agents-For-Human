# Demo script, 4:40

Screen recording with voiceover. No camera. Record in three segments and cut. 1080p, 125% browser zoom,
notifications off, dashboard window 1440px wide.

## 0:00 to 0:35 The shoebox

**Screen** `data/estate_alvarez/mail/` open in a file browser, thumbnails visible. Scroll it slowly.

**Say** "When my grandfather died, my mother became the executor. That meant a year of phone calls. Banks want
an original death certificate and won't take a copy. The pension board wants a notarized form. The gym keeps
billing and says it never got the cancellation. The research says about 500 hours and 15 months. Almost none of
those hours need judgment. They need someone who will not give up. This is Postscript."

## 0:35 to 1:10 Intake

**Screen** `postscript intake` in a terminal, then the dashboard ledger filling in.

**Say** "It starts with the shoebox. Fifteen pieces of mail, some of them scans. It found ten institutions,
merged the duplicate bank statement, and ignored the pizza flyer. Every extraction, including the ones it
rejected, is on the record."

## 1:10 to 2:30 Eight weeks in ninety seconds

**Screen** `make demo`. The activity feed and the simulated date in the header.

**Say** "Now it runs. One tick a day. Notices out, follow-ups on schedule. Northwind ignores the first letter,
so it nudges them. Redwood Fitness claims twice that they have no record of the cancellation, so it escalates
to certified mail, and they fold. Watch what it is *not* doing while all that happens. It is not paying
anything. It is not signing anything. It has not put a single original certificate in the mail."

## 2:30 to 3:30 The nine interruptions

**Screen** The decision inbox, phone-width window. Open the Sequoia decision. Approve it. Next tick, the task
resumes. Then scroll the feed to a red BLOCKED row.

**Say** "Here is everything it asked her in eight weeks. Nine questions. This one: the insurer approved the
claim and wants a payout election, lump sum or annuity. Plain language, two options, a recommendation. She taps
approve and it picks up on the next tick.

And here is the part I care about. On day three the agent tried to pay the final power bill on its own. It
didn't get to. The Cedar policy stopped the call before the tool ran, and turned it into this question instead.
The prompt asks the agent to behave. The policy is what makes sure."

## 3:30 to 4:10 The accounting

**Screen** `out/accounting_alvarez.pdf`, scroll: cover, verification stamp, decisions table, schedule of
actions with the Basis column. Then `postscript verify-chain` in the terminal.

**Say** "An executor has a legal duty to account for what they did with the estate. So every call the agent
made, every call the policy blocked, and every answer she gave is a hash-chained record, and they render into
this. One hundred and thirty-six records. Each one names the rule that allowed it or the approval it ran under.
Change any of them and the chain breaks."

## 4:10 to 4:40 The number and the architecture

**Screen** The metrics strip, then the architecture PNG, then one AgentCore trace screenshot, then the repo URL.

**Say** "Nineteen actions. Nine interruptions. An agent that confirms everything would have asked nineteen
times. It missed none of the nine decisions a real executor had to make, and it never once acted where the
policy said it needed her. Strands agents on AgentCore Runtime, Cedar in the loop before every tool call, the
institutions behind MCP, and a receipt chain underneath all of it. Thanks for watching."

## Recording checklist

- [ ] `make test` green before you record
- [ ] Fresh `postscript simulate` so the numbers on screen match the README
- [ ] Terminal font at least 16pt
- [ ] Rehearse twice; the middle segment drifts long
- [ ] Under 5:00 including titles
- [ ] Uploaded public on YouTube, link in the Devpost form
