# Contributing & sourcing standards

This database lives or dies on accuracy. Every entry must be verifiable by a
reader who follows the links. Please follow these rules.

## The one hard rule

**No claim without a source.** If you can't cite it, don't publish it. Mark the
field `"verified": false` and leave `sources` empty until a citation exists.

## Acceptable sources

Ranked roughly by strength:

1. **Primary records** — Hansard (parliamentary debate/votes), AEC disclosure
   returns, the candidate's own published platform, official APH profiles, court
   or AEC eligibility rulings.
2. **Direct statements** — the candidate's official website, verified social
   media, recorded interviews, media releases.
3. **Reputable reporting** — established news outlets, used to point back to a
   primary statement or vote.

Avoid: anonymous claims, unverified screenshots, opinion pieces presented as
fact, or anything you can't link to.

## What we record — and what we don't

- **Do** record: stated policy positions, recorded votes, public statements of
  faith, disclosed donations (AEC), and Section 44 eligibility status.
- **Don't** record: ethnicity, ancestry, national origin, or heritage; inferred
  private beliefs; or any aggregate "loyalty"/ideology score. We summarise what
  someone has said or done and let readers judge.

### The two sensitive fields

- **Citizenship** is recorded *only* as Section 44 constitutional eligibility —
  e.g. "Confirmed sole citizen" or "Renounced UK citizenship on 2017-08-01 per
  AEC". It is never a heritage flag.
- **Foreign policy** records actual positions and votes (including foreign aid
  and Middle East policy). State the position and link the source; do not grade
  it.

## How the data is organised

`data/candidates.json` is **generated** — don't hand-edit it. The inputs are:

- **Rosters:** federal members come from the AEC/OpenAustralia CSVs in
  `data/sources/`; state/territory members from `data/sources/states/*.json`;
  announced election candidates from `data/sources/candidates/*.json`. Every
  roster file carries its own source citation.
- **Positions:** hand-sourced positions live in `data/positions/<issue>.json`
  (one file per issue, 24 issues), keyed by candidate id. The build merges them
  into `candidates.json`, so they survive any roster rebuild. This is where you
  add or correct a position.
- **Photos/donors:** `data/photos.json` and `data/donor_info.json`, also keyed
  by candidate id / donor name.

Rebuild and verify with:

```
python3 scripts/build_candidates.py     # warns on orphaned position ids
python3 scripts/build_db.py && python3 scripts/db_to_json.py --check
```

There is also a relational SQLite layer (`db/README.md`) and an in-browser SQL
explorer (`explore.html`) — both are generated from the same data; you never
need to edit them directly.

## Adding or correcting a position

1. Find the candidate's `id` in `data/candidates.json`.
2. Add an entry under that id in the relevant `data/positions/<issue>.json`:
   `{ "summary": "...", "sources": [{"title","url","publisher","date"}], "verified": true }`.
3. Set `"verified": true` *only* when the `summary` is fully supported by the
   listed `sources` — and only cite sources you actually retrieved.
4. Run `python3 scripts/build_candidates.py` and commit both the position file
   and the regenerated `candidates.json`.

## Adding a candidate

New people enter via the roster files (see above), not by hand-editing
`candidates.json`. For an announced election candidate, add them to the
relevant `data/sources/candidates/*.json` with a `source_url` confirming the
candidacy. Validate against `data/schema.json` before committing.

## Corrections

Found something wrong or stale? Open an issue with a better source, or submit a
change that swaps in the correct citation. Corrections backed by a stronger
source always win.
