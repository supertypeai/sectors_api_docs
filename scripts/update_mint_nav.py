#!/usr/bin/env python3
"""
update_mint_nav.py

Rebuild the v2 API References block in mint.json from schema.json.

Each operation in the schema carries:
  - `tags`: [<tag>]          — which subgroup it belongs to
  - `x-mdx-path`             — the MDX file Mintlify renders

Top-level structure comes from `info.x-tagGroups`:
  [
    { "name": "Indonesia (IDX)", "x-sidebar-icon": "building-columns",
      "tags": ["Company Screener", "Detailed Reports", ...] },
    ...
  ]

Each tag in `tags[]` may also declare an `x-sidebar-icon`.

What we touch
-------------
Only the navigation entry with `group == "API References"` and
`version == "v2"`. Everything else in mint.json — recipes, v1 nav,
anchors, top-level keys — is left byte-identical.

Group label conventions
-----------------------
- Tag-group name "Singapore (SGX)" → sidebar section label "Singapore (SGX)"
  (used verbatim from the schema).
- Tag name "SGX - Company Screener" → subgroup label "Company Screener"
  (the "SGX - " prefix is stripped since the parent section already says SGX).

Behavior
--------
- New subgroups appear, new pages appear, removed pages disappear,
  removed subgroups disappear. The script is the source of truth for
  this block; do not hand-edit it (edit the schema instead).
- Section, subgroup, and page ordering follow the schema's declared order:
  `x-tagGroups` order for sections, tag order within each group for
  subgroups, and first-seen order in `paths` for pages within a subgroup.

Usage
-----
    python scripts/update_mint_nav.py \\
        --schema schema.json \\
        --mint mint.json

    # Dry-run:
    python scripts/update_mint_nav.py --dry-run
"""

import argparse
import json
import sys
from collections import OrderedDict


V2_API_GROUP = "API References"
V2_VERSION = "v2"


def collect_tag_to_pages(schema: dict) -> "OrderedDict[str, list[str]]":
    """
    Walk paths in declaration order; build OrderedDict mapping tag -> [mdx_path, ...].
    Operations without `x-mdx-path` or without a tag are skipped (with a warning).
    """
    tag_pages: "OrderedDict[str, list[str]]" = OrderedDict()
    seen = set()

    for path, path_item in schema.get("paths", {}).items():
        for method, op in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            mdx_path = op.get("x-mdx-path")
            if not mdx_path:
                continue
            tags = op.get("tags") or []
            if not tags:
                print(
                    f"WARNING: {method.upper()} {path} has x-mdx-path but no tag; skipping.",
                    file=sys.stderr,
                )
                continue

            tag = tags[0]
            mdx_ref = f"api-references/{mdx_path}"

            # Same MDX path may appear under multiple methods (e.g. report
            # has GET and GET-with-symbol). Only list it once.
            key = (tag, mdx_ref)
            if key in seen:
                continue
            seen.add(key)

            tag_pages.setdefault(tag, []).append(mdx_ref)

    return tag_pages


def build_v2_pages(schema: dict) -> list:
    """Build the `pages` array for the v2 API References navigation entry."""
    tag_pages = collect_tag_to_pages(schema)

    tag_meta = {t["name"]: t for t in schema.get("tags", [])}
    x_tag_groups = schema.get("info", {}).get("x-tagGroups", [])

    pages: list = []
    consumed_tags: set[str] = set()

    for group in x_tag_groups:
        section_label = group["name"]
        section_icon = group.get("x-sidebar-icon")
        subgroup_tags = group.get("tags", [])

        section_pages: list = []
        for tag in subgroup_tags:
            consumed_tags.add(tag)
            mdx_refs = tag_pages.get(tag, [])
            if not mdx_refs:
                print(
                    f"WARNING: tag '{tag}' has no operations with x-mdx-path; "
                    f"skipping subgroup.",
                    file=sys.stderr,
                )
                continue

            subgroup_label = _subgroup_label(tag, section_label)

            # If the resulting label matches the tag, and the tag is just an
            # abbreviation found in the parent section (e.g. "KLSE" in "Malaysia (KLSE)")
            # we flatten the pages directly into the section instead of creating a subgroup.
            if subgroup_label == tag and tag in section_label:
                section_pages.extend(mdx_refs)
                continue

            subgroup_icon = (tag_meta.get(tag, {}) or {}).get("x-sidebar-icon")

            sg: "OrderedDict[str, object]" = OrderedDict()
            sg["group"] = subgroup_label
            if subgroup_icon:
                sg["icon"] = subgroup_icon
            sg["pages"] = mdx_refs
            section_pages.append(sg)

        if not section_pages:
            print(
                f"WARNING: section '{section_label}' has no populated subgroups; "
                f"skipping section.",
                file=sys.stderr,
            )
            continue

        section: "OrderedDict[str, object]" = OrderedDict()
        section["group"] = section_label
        if section_icon:
            section["icon"] = section_icon
        section["pages"] = section_pages
        pages.append(section)

    orphan_tags = [t for t in tag_pages if t not in consumed_tags]
    if orphan_tags:
        print(
            f"WARNING: tags with operations but not listed in x-tagGroups: "
            f"{orphan_tags}",
            file=sys.stderr,
        )

    pages.append("api-references/v2/changelog")
    return pages


def _subgroup_label(tag: str, section_label: str) -> str:
    """
    Strip "<EXCHANGE> - " prefix if the section label already names the exchange.
    "SGX - Company Screener" under "Singapore (SGX)" -> "Company Screener".
    """
    if " - " in tag:
        prefix, rest = tag.split(" - ", 1)
        if prefix in section_label:
            return rest
    return tag


def update_mint(mint: dict, new_pages: list) -> bool:
    """Replace the v2 API References pages in-place. Returns True if changed."""
    nav = mint.get("navigation", [])
    for entry in nav:
        if entry.get("group") == V2_API_GROUP and entry.get("version") == V2_VERSION:
            if entry.get("pages") == new_pages:
                return False
            entry["pages"] = new_pages
            return True

    raise RuntimeError(
        f"Could not find navigation entry with group='{V2_API_GROUP}' and "
        f"version='{V2_VERSION}' in mint.json"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--schema", default="schema.json")
    parser.add_argument("--mint", default="mint.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the diff to stdout without writing.",
    )
    args = parser.parse_args()

    with open(args.schema, encoding="utf-8") as f:
        schema = json.load(f)
    with open(args.mint, encoding="utf-8") as f:
        mint = json.load(f, object_pairs_hook=OrderedDict)

    new_pages = build_v2_pages(schema)
    changed = update_mint(mint, new_pages)

    if not changed:
        print("mint.json v2 navigation already in sync; no changes.")
        return

    serialized = json.dumps(mint, indent=2, ensure_ascii=False) + "\n"

    if args.dry_run:
        print("[dry-run] would update v2 API References block in mint.json")
        print(
            "[dry-run] new v2 pages:\n"
            + json.dumps(new_pages, indent=2, ensure_ascii=False)
        )
        return

    with open(args.mint, "w", encoding="utf-8") as f:
        f.write(serialized)
    print(f"Updated {args.mint}: rebuilt v2 API References block.")


if __name__ == "__main__":
    main()
