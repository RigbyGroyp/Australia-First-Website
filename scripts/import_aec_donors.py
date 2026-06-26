#!/usr/bin/env python3
"""Import AEC Member-of-Parliament donor disclosures into candidates.json.

Source: AEC Transparency Register "All Annual Data" bulk download
        https://transparency.aec.gov.au/Download/AllAnnualData

This populates ONLY the `donors` field from public AEC records. Policy
positions (immigration, faith, etc.) are left empty for sourced manual entry.

IMPORTANT SCOPE NOTE: AEC *Member of Parliament* returns capture only
donations disclosed directly to an individual member. The large majority of
political money flows through party returns, not member returns — so this data
is partial and is weighted toward independents and crossbenchers, who are
required to lodge member returns. The summary text records this caveat per
candidate. Foreign-vs-domestic donor status is not flagged in this dataset, so
`source_type` is recorded as "unknown" rather than guessed.

Usage:
    python3 scripts/import_aec_donors.py path/to/aec_csv_dir
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict

REGISTER_URL = "https://transparency.aec.gov.au/MemberOfParliament"
DOWNLOAD_URL = "https://transparency.aec.gov.au/Download/AllAnnualData"
HONORIFICS = re.compile(
    r"^(Senator|Hon|Dr|Mr|Ms|Mrs|Miss|the)\.?\s+|\s+(MP|OAM|AM|AO|QC|KC|SC)\b",
    re.IGNORECASE,
)


def clean_name(raw):
    """Trim surrounding whitespace; keep the full official name for display."""
    return re.sub(r"\s+", " ", raw).strip()


def slugify(name):
    base = HONORIFICS.sub("", name)
    base = re.sub(r"\b(MP|OAM|AM|AO|QC|KC|SC|Hon|Dr|Mr|Ms|Mrs|Senator)\b", "", base, flags=re.IGNORECASE)
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "unknown"


def chamber_for(return_type):
    if "Senator" in return_type:
        return "Senate"
    return "House of Representatives"


def aec_source(name, fy):
    return {
        "title": f"AEC Member of Parliament annual return — {name} ({fy})",
        "url": REGISTER_URL,
        "publisher": "Australian Electoral Commission",
        "date": "",
    }


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main(csv_dir):
    mp_returns = load_csv(os.path.join(csv_dir, "MemberOfParliamentReturns.csv"))
    receipts = load_csv(os.path.join(csv_dir, "Detailed Receipts.csv"))

    # Per-person aggregate state, keyed by cleaned name.
    people = {}

    def ensure(name, return_type):
        key = name
        if key not in people:
            people[key] = {
                "name": name,
                "chamber": chamber_for(return_type),
                "year_totals": [],   # (fy, total, donor_count)
                "items": [],         # (fy, donor, amount)
            }
        return people[key]

    for row in mp_returns:
        name = clean_name(row["Name"])
        p = ensure(name, row["Return Type"])
        total = int(row["Total Donations Received"] or 0)
        donors = int(row["Number of Donors"] or 0)
        p["year_totals"].append((row["Financial Year"], total, donors))

    for row in receipts:
        if row["Return Type"] != "Member of HOR Return":
            continue
        name = clean_name(row["Recipient Name"])
        p = ensure(name, row["Return Type"])
        try:
            amount = float(row["Value"] or 0)
        except ValueError:
            amount = None
        p["items"].append((row["Financial Year"], clean_name(row["Received From"]), amount))

    candidates = []
    for name, p in sorted(people.items()):
        # Build a human-readable funding summary across years.
        yt = sorted(p["year_totals"], reverse=True)
        parts = [
            f"{fy}: ${total:,} across {donors} donor(s)"
            for fy, total, donors in yt
            if total or donors
        ]
        summary = (
            "Donations disclosed directly to this member in AEC Member of "
            "Parliament returns. "
            + ("; ".join(parts) + ". " if parts else "")
            + "Note: member returns capture only donations made directly to the "
            "member, not money received via a party; figures are partial."
        )

        # Itemised donor entries (only itemised receipts are individually listed).
        entries = []
        for fy, donor, amount in sorted(p["items"], reverse=True):
            entries.append({
                "donor": donor,
                "amount_aud": amount,
                "financial_year": fy,
                "source_type": "unknown",
                "sources": [aec_source(name, fy)],
            })

        latest_fy = yt[0][0] if yt else ""
        # Omit optional enum fields (status, state) when unknown — empty strings
        # are not valid against the schema's enums, and we don't guess.
        candidates.append({
            "id": slugify(name),
            "name": name,
            "party": "",
            "chamber": p["chamber"],
            "electorate": "",
            "official_page": "",
            "last_updated": "2026-06-26",
            "positions": {},
            "donors": {
                "summary": summary,
                "entries": entries,
                "sources": [aec_source(name, latest_fy)] if latest_fy else [],
            },
        })

    out = {
        "meta": {
            "description": (
                "Australian federal candidate transparency dataset. Donor data "
                "imported from AEC Member of Parliament annual returns; policy "
                "positions to be added with sources. See ../CONTRIBUTING.md."
            ),
            "donor_source": DOWNLOAD_URL,
            "last_updated": "2026-06-26",
        },
        "candidates": candidates,
    }
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    data = main(sys.argv[1])
    dest = os.path.join(os.path.dirname(__file__), "..", "data", "candidates.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(data['candidates'])} candidate record(s) to {os.path.normpath(dest)}")
