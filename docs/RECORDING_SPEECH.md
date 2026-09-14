# Recording speech

Read this out loud. Short sentences on purpose. Pause where the line breaks.

Total spoken time: about **4 minutes 10 seconds** at a normal pace. That leaves slack under the 5:00 cap.

Record in five takes and cut them together. Do not try to do it in one run.

---

## Shot 1 — the mail (0:00 – 0:32)

**On screen:** Finder open at `data/estate_alvarez/mail/`, icon view, thumbnails showing. Scroll down once,
slowly.

> My mother was the executor of my grandfather's estate.
>
> What I remember is not the grief. It's the phone calls.
>
> A year of them. The bank wouldn't take a photocopy of the death certificate. Only an original. Each original
> costs money, and you only get so many.
>
> The gym kept billing him. And kept saying it never got the cancellation letter.
>
> The research says about five hundred hours, and fifteen months.
>
> Almost none of that work needs judgment. It needs someone who won't give up.
>
> So I built one. This is Postscript.

---

## Shot 2 — intake (0:32 – 1:08)

**On screen:** terminal. Run `postscript intake`. Let the table finish. Then scroll down to the skipped line.

**Command:**
```bash
postscript intake
```

> It starts with the shoebox. Fifteen pieces of mail.
>
> It found all ten institutions. It merged the duplicate bank statement. And it threw one out — that one's a
> marketing flyer, there's no account on it.
>
> Three of these are photographs. It read those too.
>
> And when it can't read something, it says which one, and why. That's the pattern for the whole system. When
> it doesn't know, it says so, on the record.

---

## Shot 3 — eight weeks (1:08 – 2:28)

**On screen:** `make demo`. Dashboard in the browser. Watch the date climb in the header.

**Command:**
```bash
rm -rf .postscript out && postscript intake >/dev/null 2>&1 && make demo
```

> Now it runs. One tick a day.
>
> Notices go out. Follow-ups happen on schedule.
>
> Northwind ignores the first letter, so it nudges them.
>
> Redwood Fitness says twice that they have no record of the cancellation. So it escalates to certified mail.
> And they fold.
>
> Now watch what it is *not* doing while all of that happens.
>
> It isn't paying anything. It isn't signing anything. It hasn't put a single original certificate in the mail.

---

## Shot 4 — the nine questions (2:28 – 3:30)

**On screen:** decision inbox, browser window narrow like a phone. Open the Sequoia payout decision. Click
approve. Then scroll the activity feed to a red BLOCKED row.

> Here is everything it asked her in eight weeks. Nine questions.
>
> This one. The insurer approved the claim and wants a payout election. Lump sum, or annuity.
>
> Plain language. Two options. A recommendation. She taps approve, and it picks up on the next tick.
>
> And here's the part I actually care about.
>
> On day three, the agent tried to pay the final power bill on its own.
>
> It never got there. The Cedar policy stopped the call before the tool ran, and turned it into this question
> instead.
>
> The prompt asks the agent to behave. The policy is what makes sure.

---

## Shot 5 — the accounting and the number (3:30 – 4:10)

**On screen:** open `out/accounting_alvarez.pdf`. Show the cover with the verification stamp. Scroll to the
decisions table. Then the schedule of actions — point at the Basis column. Then the terminal. Then the
architecture diagram. Then the repo URL.

**Commands:**
```bash
postscript accounting && open out/accounting_alvarez.pdf
postscript verify-chain
```

> An executor has a legal duty to account for what they did with the estate.
>
> So every call the agent made, every call the policy blocked, and every answer she gave is a hashed record.
> And they render into this.
>
> A hundred and thirty-six records. Each one names the rule that allowed it, or the approval it ran under.
>
> Change any one of them, and the chain breaks.
>
> Nineteen actions. Nine interruptions.
>
> An agent that checks everything would have asked nineteen times.
>
> It missed none of the nine decisions a real executor had to make. And it never once acted where the policy
> said it needed her.
>
> Strands agents. Cedar in front of every tool call. The institutions behind MCP. And a receipt chain under all
> of it.
>
> Thanks for watching.

---

## Before you hit record

- [ ] `source .venv/bin/activate` in every terminal window
- [ ] `make test` — should say 24 passed
- [ ] Terminal font 18pt or bigger
- [ ] Do Not Disturb on, dock hidden, desktop clear
- [ ] Browser at 125% zoom, one tab only
- [ ] Reset state: `rm -rf .postscript out && postscript intake`

## Two things that will bite you

**Shot 2 with vision.** Reading the scans needs Bedrock. Set these first, or the narration won't match what's
on screen:
```bash
set -a && . ../.env && set +a
unset AWS_BEARER_TOKEN_BEDROCK
export POSTSCRIPT_MODEL=bedrock
export POSTSCRIPT_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
```
It takes about 45 seconds. Let it run, then talk over the finished table.

**Shot 3 must be offline.** Unset those variables again before `make demo`. The eight-week run on Bedrock takes
over twenty minutes. Offline it takes two seconds and the numbers come out the same every time.

```bash
unset POSTSCRIPT_MODEL POSTSCRIPT_MODEL_ID
```

If anyone asks, say it straight: intake uses vision on Bedrock, the eight-week run is the deterministic offline
clerk so the numbers reproduce. Same tools, same MCP calls, same policy.

## After

- [ ] Upload to YouTube, set to **Public** (not unlisted)
- [ ] Title: `Postscript — the executor's agent | AWS Agents for Humans`
- [ ] Put the repo link and the Render link in the description
