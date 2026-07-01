#!/usr/bin/env python3
"""Build data/candidates.json for the current (48th) federal parliament.

Merges three public sources, all committed under data/sources/:

  * aec_house_members_elected_2025.csv  — AEC Tally Room "Members Elected"
        (House: division, state, party, member). The authoritative roster of
        the 150 House members elected at the 2025 federal election.
  * openaustralia_senators.csv          — OpenAustralia.org current Senate roster
        (76 senators, with party and state encoded in the profile URI).
  * aec_mp_returns.csv / aec_mp_detailed_receipts.csv — AEC Member-of-Parliament
        annual donor returns (totals + itemised receipts).

Output: every current member as an `incumbent` record with party / electorate /
state, plus any donor data the AEC discloses for them. Members who appear in the
donor returns but are NOT in the current roster (e.g. lost their seat in 2025)
are retained as `former` so their disclosed donor data is not lost.

Policy positions are left empty — they are added separately with their own
sources (Hansard / voting records), never inferred here.

Usage:
    python3 scripts/build_candidates.py
"""

import csv
import json
import os
import re
from collections import defaultdict

from build_config import BUILD_DATE

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "data", "sources")
POS_DIR = os.path.join(HERE, "..", "data", "positions")
DEST = os.path.join(HERE, "..", "data", "candidates.json")

# Policy-position issue keys, in display priority order. Each may have a file
# data/positions/<issue>.json mapping candidate id -> {summary, sources, verified}.
ISSUES = ["faith", "immigration", "foreign_policy", "economic_nationalism", "citizenship_eligibility",
          # State/territory conscience & social issues:
          "abortion", "voluntary_assisted_dying", "gender_lgbtq", "religious_freedom", "drugs_law_order",
          # State conscience/values issues (often decided by named conscience-vote divisions):
          "gambling", "hunting", "sex_work", "native_forest_logging", "first_nations", "nuclear", "integrity",
          # Core state policy areas:
          "housing_planning", "health", "education", "transport_infrastructure", "energy",
          "environment_water", "animal_welfare"]

AEC_HOUSE_URL = "https://results.aec.gov.au/31496/Website/HouseDownloadsMenu-31496-Csv.htm"
AEC_DONOR_URL = "https://transparency.aec.gov.au/MemberOfParliament"

STATE_MAP = {
    "nsw": "NSW", "new_south_wales": "NSW",
    "victoria": "VIC", "vic": "VIC",
    "queensland": "QLD", "qld": "QLD",
    "wa": "WA", "western_australia": "WA",
    "sa": "SA", "south_australia": "SA",
    "tasmania": "TAS", "tas": "TAS",
    "act": "ACT", "australian_capital_territory": "ACT",
    "nt": "NT", "northern_territory": "NT",
}

TITLES = re.compile(r"\b(senator|hon|dr|mr|mrs|ms|miss|the|am|ao|oam|qc|kc|sc|mp)\b", re.IGNORECASE)

# Donor returns occasionally use a member's formal given name while the roster
# uses the common one. Map donor-return norm_key -> roster norm_key.
ALIASES = {
    "antony pasin": "tony pasin",
    "robert katter": "bob katter",
    "antonio zappia": "tony zappia",
}

# OpenAustralia lists a couple of Senate officeholders with a blank "-" party.
# Correct them from the public record, keyed by candidate id.
PARTY_FIX = {
    "slade-brockman-wa": "Liberal Party",
    "sue-lines-wa": "Australian Labor Party",
}

# Same-party spelling variants collapsed to one canonical name. Applied to every
# record's party field (ids never embed party, so this is rename-safe).
PARTY_CANON = {
    "Liberal": "Liberal Party",
    "National Party": "The Nationals",
    "The Greens": "Australian Greens",
    "Katter's Australian Party (KAP)": "Katter's Australian Party",
}

# Donor-only "former" records carry no roster row; backfill their last-held
# party and state (well-documented public facts) so the records aren't blank.
FORMER_FIX = {
    "andrew-laming": {"party": "Liberal National Party of Queensland", "state": "QLD"},
    "maria-vamvakinou": {"party": "Australian Labor Party", "state": "VIC"},
    "zoe-daniel": {"party": "Independent", "state": "VIC"},
    "concetta-fierravanti-wells": {"party": "Liberal Party", "state": "NSW"},
}

# Normalised party groupings for clean filtering. The exact party (as the source
# reported it) is preserved; party_group collapses source-labelling variants
# (e.g. "Liberal"/"Liberal Party", "The Nationals"/"National Party") and the
# Coalition partners into one filterable group.
PARTY_GROUP = {
    "Australian Labor Party": "Labor",
    "Territory Labor Party": "Labor",
    "Liberal": "Coalition",
    "Liberal Party": "Coalition",
    "Liberal National Party of Queensland": "Coalition",
    "Liberal National Party": "Coalition",
    "The Nationals": "Coalition",
    "National Party": "Coalition",
    "Country Liberal Party": "Coalition",
    "Australian Greens": "Greens",
    "The Greens": "Greens",
    "ACT Greens": "Greens",
    "Tasmanian Greens": "Greens",
    "Queensland Greens": "Greens",
    "Canberra Liberals": "Coalition",
    "Pauline Hanson's One Nation Party": "One Nation",
    "Family First Party": "Other / minor party",
    "Independent": "Independent",
    "Fiona Carrick Independent": "Independent",
    "Katter's Australian Party": "Other / minor party",
    "Centre Alliance": "Other / minor party",
    "Jacqui Lambie Network": "Other / minor party",
    "United Australia Party": "Other / minor party",
    "Australia's Voice": "Other / minor party",
}


def party_group(party):
    if party in PARTY_GROUP:
        return PARTY_GROUP[party]
    return "" if party in ("", "-") else "Other / minor party"


def proper_case(surname):
    """Convert an all-caps AEC surname to proper case, preserving Mc, apostrophes
    and hyphens (ALBANESE->Albanese, McBAIN->McBain, O'BRIEN->O'Brien)."""
    def cap(w):
        if not w:
            return w
        if w[:2].lower() == "mc" and len(w) > 2:
            return "Mc" + w[2].upper() + w[3:].lower()
        return w[:1].upper() + w[1:].lower()
    parts = re.split(r"([-' ])", surname)
    return "".join(p if p in "-' " else cap(p) for p in parts)


def norm_key(name):
    """Normalise a personal name to 'first last' lowercase, titles stripped."""
    n = TITLES.sub(" ", name)
    n = re.sub(r"[^a-zA-Z\s'-]", " ", n)
    tokens = [t for t in re.split(r"\s+", n.strip().lower()) if t]
    if not tokens:
        return ""
    # Use first + last token only — robust to middle names / honorific noise.
    return f"{tokens[0]} {tokens[-1]}" if len(tokens) > 1 else tokens[0]


def slugify(name, suffix=""):
    def clean(s):
        return re.sub(r"[^a-zA-Z0-9]+", "-", TITLES.sub(" ", s)).strip("-").lower()
    base = clean(name)
    return f"{base}-{clean(suffix)}".strip("-") if suffix else base


def read_csv(path, skip=0):
    with open(path, newline="", encoding="utf-8-sig") as f:
        for _ in range(skip):
            next(f)
        return list(csv.DictReader(f))


def aec_donor_source(name, fy):
    return {
        "title": f"AEC Member of Parliament annual return — {name} ({fy})".strip(),
        "url": AEC_DONOR_URL,
        "publisher": "Australian Electoral Commission",
        "date": "",
    }


def build_donors():
    """Return {norm_key: (display_name, chamber, donor_block)} from AEC returns."""
    import donor_info as donor_info_mod
    registry = donor_info_mod.load()
    totals = defaultdict(list)   # name -> [(fy, total, count)]
    items = defaultdict(list)    # name -> [(fy, donor, amount)]
    chamber_of = {}

    def to_int(raw):
        """Parse an AEC count/amount cell tolerantly ('1,500', '$1500', '1500.00')."""
        cleaned = re.sub(r"[^0-9.\-]", "", raw or "")
        try:
            return int(float(cleaned)) if cleaned else 0
        except ValueError:
            return 0

    for row in read_csv(os.path.join(SRC, "aec_mp_returns.csv")):
        name = re.sub(r"\s+", " ", row["Name"]).strip()
        chamber_of[name] = "Senate" if "Senator" in row["Return Type"] else "House of Representatives"
        totals[name].append((row["Financial Year"], to_int(row["Total Donations Received"]),
                             to_int(row["Number of Donors"])))

    for row in read_csv(os.path.join(SRC, "aec_mp_detailed_receipts.csv")):
        if row["Return Type"] != "Member of HOR Return":
            continue
        name = re.sub(r"\s+", " ", row["Recipient Name"]).strip()
        try:
            amount = float(row["Value"] or 0)
        except ValueError:
            amount = None
        items[name].append((row["Financial Year"], re.sub(r"\s+", " ", row["Received From"]).strip(), amount))

    donors = {}
    for name in totals:
        yt = sorted(totals[name], reverse=True)
        grand_total = sum(total for _, total, _ in yt)
        chamber = chamber_of.get(name, "House of Representatives")
        parts = [f"{fy}: ${total:,} across {cnt} donor(s)" for fy, total, cnt in yt if total or cnt]
        summary = (
            "Donations disclosed directly to this member in AEC Member of Parliament returns. "
            + ("; ".join(parts) + ". " if parts else "")
            + "Note: member returns capture only donations made directly to the member, "
            "not money received via a party; figures are partial."
        )
        # The AEC detailed-receipts export itemises House returns only, so a
        # senator can legitimately show a total with no itemised entries.
        if chamber == "Senate" and grand_total and not items.get(name):
            summary += " Itemised receipts are published for House members only."
        entries = []
        for fy, donor, amount in sorted(items.get(name, []), reverse=True):
            entry = {"donor": donor, "amount_aud": amount, "financial_year": fy,
                     "source_type": "unknown", "sources": [aec_donor_source(name, fy)]}
            info = donor_info_mod.info_for(donor, registry)
            if info:
                entry["info"] = info
            entries.append(entry)
        latest_fy = yt[0][0] if yt else ""
        key = norm_key(name)
        key = ALIASES.get(key, key)
        if key in donors:
            print(f"WARNING: donor-return name collision on '{key}' "
                  f"({donors[key][0]!r} vs {name!r}) — second entry wins; verify attribution.")
        donors[key] = (name, chamber, {
            "summary": summary,
            "total_aud": grand_total,
            "entries": entries,
            "sources": [aec_donor_source(name, latest_fy)] if latest_fy else [],
        })
    return donors


def build_roster():
    """Return list of incumbent records and the set of norm_keys present."""
    records, keys = [], set()

    # House — AEC Members Elected (authoritative). File has a 1-line metadata
    # banner above the header row.
    for row in read_csv(os.path.join(SRC, "aec_house_members_elected_2025.csv"), skip=1):
        given, surname = row["GivenNm"].strip(), proper_case(row["Surname"].strip())
        name = f"{given} {surname}".strip()
        key = norm_key(name)
        keys.add(key)
        records.append({
            "id": slugify(name, row["DivisionNm"].lower()),
            "name": name,
            "party": row["PartyNm"].strip(),
            "chamber": "House of Representatives",
            "electorate": row["DivisionNm"].strip(),
            "state": row["StateAb"].strip(),
            "status": "incumbent",
            "official_page": "",
            "last_updated": BUILD_DATE,
            "positions": {},
            "_key": key,
            "_source": {
                "title": f"AEC 2025 Federal Election — Members Elected ({row['DivisionNm']}, {row['StateAb']})",
                "url": AEC_HOUSE_URL,
                "publisher": "Australian Electoral Commission",
                "date": "2025-06-16",
            },
        })

    # Senate — OpenAustralia current roster (state encoded in URI tail).
    for row in read_csv(os.path.join(SRC, "openaustralia_senators.csv")):
        name = re.sub(r"\s+", " ", row["Name"]).strip()
        state_tail = row["URI"].rstrip("/").rsplit("/", 1)[-1].lower()
        state = STATE_MAP.get(state_tail, "")
        key = norm_key(name)
        keys.add(key)
        rec = {
            "id": slugify(name, state.lower()),
            "name": name,
            "party": row["Party"].strip(),
            "chamber": "Senate",
            "status": "incumbent",
            "official_page": row["URI"].strip(),
            "last_updated": BUILD_DATE,
            "positions": {},
            "_key": key,
            "_source": {
                "title": f"OpenAustralia.org — Senator profile ({name})",
                "url": row["URI"].strip(),
                "publisher": "OpenAustralia.org",
                "date": "",
            },
        }
        if state:
            rec["state"] = state
        records.append(rec)

    return records, keys


def load_state_rosters():
    """Build records for state/territory members from data/sources/states/*.json.
    Federal data comes from the AEC/OpenAustralia pipeline; states are simpler
    roster files (no donor data — state disclosure regimes differ per jurisdiction)."""
    import glob as _glob
    states_dir = os.path.join(SRC, "states")
    records = []
    for path in sorted(_glob.glob(os.path.join(states_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            j = json.load(f)
        jur = j["jurisdiction"]
        for m in j["members"]:
            name = m["name"].strip()
            electorate = m.get("electorate", "")
            rec = {
                "id": f"{jur.lower().replace(' ', '-')}-{slugify(name, electorate)}",
                "name": name,
                "party": m["party"],
                "party_group": party_group(m["party"]),
                "jurisdiction": jur,
                "chamber": m.get("chamber", j.get("chamber", "")),
                "electorate": electorate,
                "state": j.get("state", ""),
                "status": "incumbent",
                "last_updated": BUILD_DATE,
                "positions": {},
                "roster_source": j["source"],
            }
            records.append(rec)
    return records


def load_candidate_rosters():
    """Build records for people RUNNING at an upcoming election (non-incumbents),
    from data/sources/candidates/*.json. These are kept separate from incumbents
    via status="candidate" and an `election` field; the front end shows them in
    their own section. No donor data (they are not members)."""
    import glob as _glob
    from urllib.parse import urlparse
    cdir = os.path.join(SRC, "candidates")
    records = []
    for path in sorted(_glob.glob(os.path.join(cdir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            j = json.load(f)
        election = j["election"]
        elslug = re.sub(r"[^a-z0-9]+", "-", election.lower()).strip("-")
        for m in j["candidates"]:
            name = m["name"].strip()
            electorate = m.get("electorate", "")
            rec = {
                "id": f"{elslug}-{slugify(name, electorate)}",
                "name": name,
                "party": m["party"],
                "party_group": party_group(m["party"]),
                "jurisdiction": j.get("jurisdiction", ""),
                "chamber": m.get("chamber", j.get("chamber", "")),
                "electorate": electorate,
                "state": j.get("state", ""),
                "status": "candidate",
                "election": election,
                "poll_date": j.get("poll_date", ""),
                "last_updated": BUILD_DATE,
                "positions": {},
                "roster_source": j["source"],
            }
            url = m.get("source_url")
            if url:
                rec["candidacy_source"] = {
                    "title": f"Candidacy confirmed — {name} ({electorate})",
                    "url": url,
                    "publisher": urlparse(url).netloc.replace("www.", ""),
                    "date": "",
                }
            records.append(rec)
    return records


def load_photos():
    """Load member portrait URLs (Wikipedia/Wikimedia Commons) keyed by id."""
    path = os.path.join(HERE, "..", "data", "photos.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_positions():
    """Load hand-sourced positions, merged by candidate id. Rebuild-safe:
    positions live in data/positions/<issue>.json, never in candidates.json."""
    positions = defaultdict(dict)  # candidate id -> {issue: position}
    if not os.path.isdir(POS_DIR):
        return positions
    # A position file for an issue missing from ISSUES would be silently
    # ignored — that's how sourced data quietly disappears. Warn instead.
    unknown = sorted(os.path.splitext(f)[0] for f in os.listdir(POS_DIR)
                     if f.endswith(".json") and os.path.splitext(f)[0] not in ISSUES)
    for stem in unknown:
        print(f"WARNING: data/positions/{stem}.json is not in ISSUES and will be ignored.")
    for issue in ISSUES:
        path = os.path.join(POS_DIR, f"{issue}.json")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for cand_id, pos in data.items():
            positions[cand_id][issue] = pos
    return positions


def attach_positions(records, positions):
    matched = 0
    ids = {rec["id"] for rec in records}
    orphans = sorted(set(positions) - ids)
    if orphans:
        print(f"WARNING: {len(orphans)} position key(s) match no roster id "
              f"(sourced data NOT included): {orphans}")
    for rec in records:
        pos = positions.get(rec["id"])
        if not pos:
            continue
        # Preserve ISSUES display order.
        rec["positions"] = {k: pos[k] for k in ISSUES if k in pos}
        matched += 1
    return matched


def main():
    donors = build_donors()
    roster, roster_keys = build_roster()

    matched = 0
    for rec in roster:
        key = rec.pop("_key")
        roster_source = rec.pop("_source")
        # Attach a roster source on the record's donors block if no donor data,
        # so even members with no disclosed donations carry a citation for the
        # roster fact (party/electorate/state).
        if key in donors:
            _, _, donor_block = donors[key]
            rec["donors"] = donor_block
            matched += 1
        else:
            rec["donors"] = {
                "summary": "No donations disclosed directly to this member in AEC "
                           "Member of Parliament returns (money received via a party "
                           "is not attributed to individuals).",
                "total_aud": 0,
                "entries": [],
                "sources": [],
            }
        rec["roster_source"] = roster_source

    # Donor-only people not in the current roster -> retain as former.
    former = []
    for key, (name, chamber, donor_block) in donors.items():
        if key in roster_keys:
            continue
        rec_id = slugify(name)
        fix = FORMER_FIX.get(rec_id, {})
        rec = {
            "id": rec_id,
            "name": name,
            "party": fix.get("party", ""),
            "chamber": chamber,
            "status": "former",
            "last_updated": BUILD_DATE,
            "positions": {},
            "donors": donor_block,
        }
        if fix.get("state"):
            rec["state"] = fix["state"]
        former.append(rec)

    all_records = sorted(roster, key=lambda r: (r["chamber"], r.get("state", ""), r["name"])) + \
        sorted(former, key=lambda r: r["name"])

    # Correct blank party values, then tag each record with a normalised group.
    for rec in all_records:
        if rec["id"] in PARTY_FIX:
            rec["party"] = PARTY_FIX[rec["id"]]
        if rec.get("party") == "-":
            rec["party"] = ""
        rec["party_group"] = party_group(rec.get("party", ""))
        rec["jurisdiction"] = "Federal"

    # Append state/territory members and upcoming-election candidates
    # (roster only; positions/photos merge below).
    all_records += load_state_rosters()
    all_records += load_candidate_rosters()

    # Collapse party spelling variants, then recompute the group off the
    # canonical name so both fields stay consistent.
    for rec in all_records:
        if rec.get("party") in PARTY_CANON:
            rec["party"] = PARTY_CANON[rec["party"]]
            rec["party_group"] = party_group(rec["party"])

    # Ids are generated by five independent code paths; a collision would let
    # positions/photos attach to the wrong person and crash build_db later.
    seen, dupes = set(), set()
    for rec in all_records:
        if rec["id"] in seen:
            dupes.add(rec["id"])
        seen.add(rec["id"])
    if dupes:
        raise SystemExit(f"FATAL: duplicate candidate id(s): {sorted(dupes)}")

    photos = load_photos()
    for rec in all_records:
        ph = photos.get(rec["id"])
        if ph:
            rec["photo_url"] = ph["photo_url"]
            rec["photo_credit_url"] = ph.get("page_url", "")

    positions = load_positions()
    pos_matched = attach_positions(all_records, positions)

    out = {
        "meta": {
            "description": "Australian candidate transparency dataset: the federal 48th Parliament, "
                           "all eight state/territory parliaments (see jurisdiction field), and "
                           "announced candidates for upcoming elections (status='candidate', e.g. "
                           "Victoria 2026). Federal roster from AEC Members Elected (House) and "
                           "OpenAustralia (Senate) with AEC donor data; state rosters from "
                           "data/sources/states/; election candidates from data/sources/candidates/. "
                           "Sourced positions across 24 issues (5 federal, 19 state) are added "
                           "separately from data/positions/. See ../CONTRIBUTING.md.",
            "house_source": AEC_HOUSE_URL,
            "senate_source": "https://www.openaustralia.org.au/senators/",
            "donor_source": AEC_DONOR_URL,
            "last_updated": BUILD_DATE,
        },
        "candidates": all_records,
    }
    with open(DEST, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(all_records)} records "
          f"({len(roster)} incumbents, {len(former)} former).")
    print(f"Donor records matched to current members: {matched}/{len(donors)}.")
    print(f"Records with hand-sourced positions: {pos_matched}.")
    print(f"Records with a portrait: {sum(1 for r in all_records if r.get('photo_url'))}.")
    if former:
        print("Retained as former (donor data, not in current roster):")
        for r in former:
            print(f"  - {r['name']} ({r['chamber']})")


if __name__ == "__main__":
    main()
