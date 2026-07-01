"""Shared build constants.

BUILD_DATE stamps every record's last_updated and the meta blocks. It is manual
by design: deriving it from today() would rewrite every record on each rebuild
and drown real changes in diff noise. Bump it when the data meaningfully changes.
"""
BUILD_DATE = "2026-07-01"
