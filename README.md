# Australian Candidate Transparency Database

A factual, fully-sourced reference on Australian politicians and candidates —
covering the **federal Parliament, all eight state and territory parliaments,
and announced candidates for upcoming elections** (currently Victoria 2026).

The goal is to help voters make informed decisions by gathering **publicly
available, verifiable information** about where candidates stand, with a source
link attached to every claim. This is an information resource, not a scorecard.

**Current scope:** 991 records — 846 sitting members (226 federal + 620
state/territory), 141 announced election candidates, and 4 former members
retained for their disclosed donor data. 644 records carry at least one sourced
position; 540 have a portrait; 726 donors are profiled with a link and
description.

## What it tracks

Sourced, factual information across **24 issues**:

**Federal issues** (federal members only — states don't legislate these):

| Issue | What it covers |
|-------|----------------|
| Immigration | Stated policy positions and recorded votes. |
| Faith & religion | Publicly stated faith and on-record statements. Self-disclosed only. |
| Economic nationalism | Manufacturing self-sufficiency, procurement, foreign ownership. |
| Foreign policy & aid | Recorded positions and votes, incl. Middle East policy and aid. |
| Citizenship eligibility | Section 44 constitutional eligibility only (sole vs dual citizenship). |

**Conscience & social issues** (tracked for state members; often decided by
named conscience-vote divisions in Hansard): abortion, voluntary assisted
dying, gender & LGBTQ+ policy, religious freedom, drugs & law and order,
gambling reform, hunting, sex work, First Nations & treaty, integrity &
anti-corruption.

**State policy areas:** native forest logging, nuclear & uranium, housing &
planning, health, education, transport & infrastructure, energy, environment &
water, animal welfare.

**Donors:** disclosed donations both **to individual members** (AEC Member of
Parliament returns) and **to parties** (AEC detailed receipts, per financial
year), with a donor-information registry that links each identifiable
organisation to its own website and a short sourced description of who it is.

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
  schema.json               JSON Schema all candidate records validate against
  candidates.json           The dataset (generated — do not hand-edit)
  positions/<issue>.json    Hand-sourced positions, one file per issue, keyed by
                            candidate id (rebuild-safe; merged by the build)
  photos.json               Portrait URLs (Wikimedia Commons via Wikipedia + OpenAustralia)
  party_donations.json      Disclosed donations TO parties (AEC detailed receipts)
  donor_info.json           Donor registry: link + sourced description per donor
  party_positions.json      Federal party-platform fallbacks
  sources/                  Committed inputs: AEC/OpenAustralia CSVs,
                            states/*.json rosters, candidates/*.json election rosters
db/
  schema.sql                Relational schema for the SQLite layer
  candidates.sql            Deterministic full-dataset SQL dump (diffable, committed)
  README.md                 The relational model, donor consolidation, example queries
index.html                  Searchable, filterable front-end (static, no build step)
explore.html                In-browser SQL explorer (sql.js/WASM, fully client-side)
assets/
  style.css, app.js, explore.js
  vendor/sqljs/             Vendored sql.js (no third-party requests)
scripts/
  build_candidates.py       Builds candidates.json (rosters + positions + photos)
  build_party_donations.py  Builds party_donations.json
  build_db.py               JSON -> data/candidates.db (SQLite) + db/candidates.sql
  db_to_json.py             SQLite -> JSON; --check verifies round-trip parity
  consolidate_donors.py     Maps donor spelling variants to canonical entities
  fetch_photos.py           Wikipedia portraits (merges; never clobbers)
  backfill_photos.py        OpenAustralia portrait backfill (federal)
CONTRIBUTING.md             Sourcing standards and how to add/correct an entry
```

## How the dataset is built

`data/candidates.json` is generated by `scripts/build_candidates.py` from
committed sources under `data/sources/`:

| Source | Origin | Provides |
|---|---|---|
| `aec_house_members_elected_2025.csv` | [AEC Tally Room](https://results.aec.gov.au/31496/Website/HouseDownloadsMenu-31496-Csv.htm) | 150 House members |
| `openaustralia_senators.csv` | [OpenAustralia.org](https://www.openaustralia.org.au/senators/) | 76 senators |
| `aec_mp_returns.csv`, `aec_mp_detailed_receipts.csv` | [AEC Transparency Register](https://transparency.aec.gov.au/MemberOfParliament) | member donor data |
| `states/*.json` | State parliament rosters (each cites its source) | 620 state/territory members |
| `candidates/*.json` | Election candidate rosters (per-candidate citations) | announced candidates |

To rebuild after updating any source:

```
python3 scripts/build_candidates.py     # validates ids, warns on orphaned positions
python3 scripts/build_party_donations.py
python3 scripts/build_db.py             # SQLite + SQL dump (also run at deploy)
python3 scripts/db_to_json.py --check   # round-trip parity check
```

Every member carries a `roster_source` citation; every running candidate
carries a `candidacy_source` confirming they are standing.

**Donor-data scope caveat:** AEC *Member of Parliament* returns only capture
donations made **directly to a member** — most political money flows through
party returns, so per-member donor data is partial and weighted toward
independents. Itemised receipts are published for House members only. Each
record's summary states this.

## Party donations & donor information

The **Party donations** tab shows donations made *to parties* (AEC detailed
receipts, `Donation Received` only), per financial year (2021-22 to 2024-25),
with branch returns grouped into party families. A **donor search** works
across all parties. Donor names are kept exactly as disclosed (the same entity
may appear under several spellings); the SQLite layer's `canonical_id` maps 152
spelling variants to 112 entities for roll-up queries.

726 identifiable organisation donors carry a link to their own website/social
media and a short, sourced description of who they are — so readers can see
what the source of a donation actually is.

## SQL explorer

`explore.html` lets anyone run SQL over the whole dataset **in their browser**
(sql.js/WASM, vendored — no server, no third-party requests, nothing sent
anywhere). The GitHub Pages workflow builds `data/candidates.db` at deploy time.
Example queries ship on the page; the relational model is documented in
`db/README.md`.

## Running it

Static site — no build step:

```
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Position coverage

Coverage is partial **by design**: a position is recorded only where it is
concretely stated and backed by a source that was actually retrieved — never
inferred from party membership, never guessed. Faith is recorded only where
self-disclosed or publicly reported with a citation, never inferred from a
name, ancestry, or schooling. The same evidence bar applies to every issue.

Top issues by sourced positions: voluntary assisted dying (283), abortion
(265), drugs & law and order (186), gender & LGBTQ+ (134), religious freedom
(130), faith (102), immigration (95), First Nations & treaty (92), foreign
policy (81), economic nationalism (73), sex work (63), nuclear (45). Issues
decided by named Hansard divisions yield the deepest per-person coverage;
executive-driven policy areas surface mainly ministers with sourced records.

Portraits come from each member's Wikipedia article (Wikimedia Commons) via
`scripts/fetch_photos.py`, with OpenAustralia backfill for federal members
(`scripts/backfill_photos.py`, which rejects placeholder images). A portrait is
attached only when the resolved page is described as a politician and the
surname matches — the wrong person's photo is never shown. Each portrait links
to its source page for attribution.

## Roadmap

- [x] Federal House + Senate roster, donors, positions, portraits
- [x] All eight state/territory parliaments (ACT, NT, TAS, QLD, SA, NSW, VIC, WA)
- [x] 19 state-issue categories incl. named conscience-vote divisions
- [x] Party donations with per-year breakdown and donor search
- [x] Donor-information registry (726 organisations profiled)
- [x] SQLite relational layer + in-browser SQL explorer
- [x] Running candidates for upcoming elections (Victoria 2026)
- [ ] State electoral-commission donation disclosures (per-state regimes)
- [ ] Victoria 2026 Legislative Council + minor-party candidates
