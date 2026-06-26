# Australian Federal Candidate Transparency Database

A factual, fully-sourced reference on Australian federal political candidates and
sitting members — covering the House of Representatives and the Senate.

The goal is to help voters make informed decisions by gathering **publicly
available, verifiable information** about where candidates stand, with a source
link attached to every claim. This is an information resource, not a scorecard.

## What it tracks

For each candidate, the database records sourced, factual information across:

| Field | What it covers |
|-------|----------------|
| **Immigration** | Stated policy positions and recorded votes on immigration. |
| **Faith & religion** | Publicly stated faith, denomination, and on-record statements about religion. Public statements only. |
| **Economic nationalism** | Positions/votes on local infrastructure, manufacturing self-sufficiency, local employment, procurement, and foreign ownership. |
| **Foreign policy & aid** | Recorded foreign-policy positions and votes, including Middle East policy and foreign aid. |
| **Citizenship eligibility** | Section 44 constitutional eligibility status (sole vs dual citizenship as it affects eligibility to sit). |
| **Donors** | Disclosed campaign donors, amounts, and domestic-vs-foreign source, from public AEC records. |

## Editorial principles

These are non-negotiable and are enforced by the data schema:

1. **Every claim needs a source.** No field is published without at least one
   citation (Hansard, AEC disclosure, party platform, or an on-the-record
   public statement). Entries lacking sources are flagged as `unverified`.
2. **Record positions; don't grade loyalty.** We summarise what a candidate has
   actually said or done and link the source. We do not assign an overall
   ideological score. Visitors draw their own conclusions.
3. **Public record only.** We track public statements and conduct. We do not
   infer private belief, and we do not record ethnicity, ancestry, or heritage.
4. **Citizenship = constitutional eligibility.** The citizenship field exists
   solely to record Section 44 eligibility (a genuine legal matter), never as a
   heritage or origin flag.
5. **Corrections welcome.** If a source is wrong or outdated, anyone can open an
   issue with a better source and the entry will be updated.

## Structure

```
data/
  schema.json        JSON Schema all candidate records must validate against
  candidates.json    The candidate dataset
index.html           Searchable, filterable front-end (static, no build step)
assets/
  style.css
  app.js
CONTRIBUTING.md      Sourcing standards and how to add/correct an entry
```

## Running it

It's a static site — no build step. Open `index.html` locally, or serve the
folder:

```
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Roadmap

- [x] Federal House of Representatives + Senate schema and front-end
- [ ] Populate federal sitting members with sourced entries
- [ ] State and territory parliaments
