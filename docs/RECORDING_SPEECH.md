# Recording script

Read the quoted lines out loud. Short sentences on purpose. Pause at each line break.

**Spoken time: about 4 minutes 5 seconds.** That leaves room under the 5:00 cap.

Record five takes and cut them together. Do not try it in one run — the middle one always drifts.

---

## Setup, once, before you record

```bash
cd /Users/mac001/Downloads/aws_hackathon/postscript
source .venv/bin/activate
make test                       # should say 24 passed
rm -rf .postscript out && postscript intake
```

- Terminal font **18pt or bigger**
- Do Not Disturb on, dock hidden, desktop cleared
- Browser at 125% zoom, **one tab**, no bookmarks bar
- Have `https://executors-agent.onrender.com` open in a second tab for the last shot

---

## Shot 1 — the mail · 0:00–0:32

**Screen:** Finder at `data/estate_alvarez/mail/`, icon view, thumbnails on. Scroll down once, slowly.

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

## Shot 2 — intake · 0:32–1:05

**Screen:** terminal. Run it, let the table land, then scroll to the `skipped:` line.

```bash
postscript intake
```

> It starts with the shoebox. Fifteen pieces of mail.
>
> It found all ten institutions. It merged the duplicate bank statement. And it threw one out — no account
> number on it, so it's not relevant.
>
> Three of these are photographs. Reading those needs vision on Bedrock. Offline, it tells you exactly which
> ones it skipped and why.
>
> That's the pattern for the whole system. When it doesn't know, it says so, on the record.

**Optional upgrade — costs 45 seconds, worth it.** Run intake against real Claude on Bedrock and it reads the
photographs and names the flyer itself. If you do this, change the middle line to *"Three of these are
photographs. It read those too — and that one it threw out as a marketing flyer."*

```bash
set -a && . ../.env && set +a
unset AWS_BEARER_TOKEN_BEDROCK
export POSTSCRIPT_MODEL=bedrock
export POSTSCRIPT_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
postscript intake
```

**Then unset it again before Shot 3** or the next shot takes twenty minutes:

```bash
unset POSTSCRIPT_MODEL POSTSCRIPT_MODEL_ID
```

---

## Shot 3 — eight weeks · 1:05–2:25

**Screen:** `make demo`. Dashboard in the browser. Watch the date climb in the masthead.

```bash
rm -rf .postscript out && postscript intake >/dev/null 2>&1 && make demo
```

> Now it runs. One tick a day.
>
> Notices go out. Follow-ups happen on schedule.
>
> Northwind ignores the first letter, so it nudges them.
>
> Redwood Fitness says twice they have no record of the cancellation. So it escalates to certified mail.
> And they fold.
>
> Now watch what it is *not* doing while all of that happens.
>
> It isn't paying anything. It isn't signing anything. It hasn't put a single original certificate in the mail.

---

## Shot 4 — the nine questions · 2:25–3:25

**Screen:** the Decision inbox panel. Scroll it slowly. Stop on the **Pacific Coast Power** card — the one with
the red **"policy caught it"** badge. Then the Activity feed, and its red BLOCKED rows.

> Here is everything it asked her in eight weeks. Nine questions.
>
> Each one is tagged with which gate it tripped. D2, an original leaving her hands. D3, a signature. D4,
> something that can't be undone.
>
> And here's the part I actually care about.
>
> On day three, the agent tried to pay the final power bill on its own.
>
> It never got there. Cedar stopped the call before the tool ran, and turned it into this question instead.
> That's what the red badge means.
>
> The prompt asks the agent to behave. The policy is what makes sure.

---

## Shot 5 — the accounting, the number, and it's live · 3:25–4:05

**Screen:** open the PDF. Cover with the verification stamp, then the decisions table, then the schedule of
actions — point at the **Basis** column. Then the terminal. Then scroll the dashboard to **The interruption
budget**. Then the second browser tab with the live URL.

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
> *(switch to the interruption budget graphic)*
>
> Nine times it stopped and asked. Ten it finished on its own. An agent that confirms everything would have
> asked nineteen times.
>
> It missed none of the nine decisions a real executor had to make. And it never once acted where the policy
> said it needed her.
>
> *(switch to the live tab)*
>
> And it's running right now. Strands agents, Cedar in front of every tool call, the institutions behind MCP,
> and a receipt chain under all of it.
>
> Thanks for watching.

---

## After

- [ ] Upload to YouTube, **Public** (not unlisted)
- [ ] Title: `Postscript — the executor's agent | AWS Agents for Humans`
- [ ] In the description:
      `Live: https://executors-agent.onrender.com`
      `Code: https://github.com/Abhinav0905/AWS-Agents-For-Human`
- [ ] Check it is under 5:00 including any title card

## If you fall behind

Cut Shot 1 to three sentences — stop after "Only an original." It's the one shot that can lose twelve seconds
without losing the point.
