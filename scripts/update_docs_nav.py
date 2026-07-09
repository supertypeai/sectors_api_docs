#!/usr/bin/env python3
"""
update_docs_nav.py

Rebuild the v2 "API References" group inside docs.json from schema.json.

Mintlify's `docs.json` structure (superseded `mint.json` in mid-2026):

    navigation.versions[]                    # one entry per docs version
        .anchors[]                           # top-nav pills (Documentation, Recipes, ...)
            .groups[]                        # sidebar groups per anchor
                .pages[]                     # pages or nested groups

We target exactly one path:

    version == "v2"
      -> anchor "Documentation"
        -> group "API References"
          -> pages[]     <-- rewritten from schema

Every operation in schema.json carries:
  - `tags`: [<tag>]     — which subgroup it belongs to
  - `x-mdx-path`        — the MDX file Mintlify renders

Top-level structure comes from `info.x-tagGroups`:
    [
      { "name": "Indonesia (IDX)", "x-sidebar-icon": "building-columns",
        "tags": ["Company Screener", "Detailed Reports", ...] },
      ...
    ]

Each tag in the top-level `tags[]` array may also carry an `x-sidebar-icon`.

What we touch
-------------
Only the v2 "API References" group's `pages` array. Everything else in
docs.json — Recipes anchor, v1 nav, top-level keys, theme, integrations,
footer — is left byte-identical.

Group label conventions
-----------------------
- Tag-group name "Singapore (SGX)" -> sidebar section label "Singapore (SGX)"
  (used verbatim from the schema).
- Tag name "SGX - Company Screener" under "Singapore (SGX)" -> subgroup
  label "Company Screener" (the "SGX - " prefix is stripped because the
  parent section already names the exchange).
- When a tag equals the exchange abbreviation already in the parent label
  (e.g. tag "KLSE" under "Malaysia (KLSE)"), we flatten the pages directly
  into the section instead of creating a redundant one-level subgroup.

Behavior
--------
- New subgroups appear, new pages appear, removed pages disappear,
  removed subgroups disappear. The script is the source of truth for
  this block; do not hand-edit it (edit the schema instead).
- Section, subgroup, and page ordering follow the schema's declared order:
  `x-tagGroups` order for sections, tag order within each group for
  subgroups, and first-seen order in `paths` for pages within a subgroup.
- Appends `api-references/v2/changelog` at the end (unchanged from prior
  convention).

Usage
-----
    python scripts/update_docs_nav.py \\
        --schema schema.json \\
        --docs docs.json

    # Dry-run:
    python scripts/update_docs_nav.py --dry-run
"""

import argparse
import json
import sys
from collections import OrderedDict


V2_VERSION = "v2"
DOC_ANCHOR = "Documentation"
API_GROUP = "API References"


def collect_tag_to_pages(schema: dict) -> "OrderedDict[str, list[str]]":
    """
    Walk paths in declaration order; build OrderedDict mapping tag -> [mdx_ref, ...].
    Operations without `x-mdx-path` or without a tag are skipped (with a warning).
    """
    tag_pages: "OrderedDict[str, list[str]]" = OrderedDict()
    seen: set = set()

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

            key = (tag, mdx_ref)
            if key in seen:
                continue
            seen.add(key)

            tag_pages.setdefault(tag, []).append(mdx_ref)

    return tag_pages


def build_v2_pages(schema: dict) -> list:
    """Build the `pages` array for the v2 API References group."""
    tag_pages = collect_tag_to_pages(schema)

    tag_meta = {t["name"]: t for t in schema.get("tags", [])}
    x_tag_groups = schema.get("info", {}).get("x-tagGroups", [])

    pages: list = []
    consumed_tags: set = set()

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

            # If the tag is just the exchange abbreviation (e.g. "KLSE") already
            # named in the parent section, flatten pages directly under the section.
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
    Strip "<EXCHANGE> - " prefix when the section label already names the exchange.
    "SGX - Company Screener" under "Singapore (SGX)" -> "Company Screener".
    """
    if " - " in tag:
        prefix, rest = tag.split(" - ", 1)
        if prefix in section_label:
            return rest
    return tag


def update_docs(docs: dict, new_pages: list) -> bool:
    """
    Replace the v2 -> Documentation -> API References -> pages array in-place.
    Returns True if changed. Raises RuntimeError if the target path is missing.
    """
    navigation = docs.get("navigation", {})
    versions = navigation.get("versions", [])

    for version_entry in versions:
        if version_entry.get("version") != V2_VERSION:
            continue

        for anchor in version_entry.get("anchors", []):
            if anchor.get("anchor") != DOC_ANCHOR:
                continue

            for grp in anchor.get("groups", []):
                if grp.get("group") != API_GROUP:
                    continue

                if grp.get("pages") == new_pages:
                    return False
                grp["pages"] = new_pages
                return True

    raise RuntimeError(
        f"Could not find navigation path: "
        f"versions[version='{V2_VERSION}'].anchors[anchor='{DOC_ANCHOR}']"
        f".groups[group='{API_GROUP}'] in docs.json"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--schema", default="schema.json")
    parser.add_argument("--docs", default="docs.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing.",
    )
    args = parser.parse_args()

    with open(args.schema, encoding="utf-8") as f:
        schema = json.load(f)
    with open(args.docs, encoding="utf-8") as f:
        docs = json.load(f, object_pairs_hook=OrderedDict)

    new_pages = build_v2_pages(schema)
    changed = update_docs(docs, new_pages)

    if not changed:
        print(f"{args.docs} v2 API References already in sync; no changes.")
        return

    serialized = json.dumps(docs, indent=2, ensure_ascii=False) + "\n"

    if args.dry_run:
        print(f"[dry-run] would update v2 API References group in {args.docs}")
        print(
            "[dry-run] new v2 API References pages:\n"
            + json.dumps(new_pages, indent=2, ensure_ascii=False)
        )
        return

    with open(args.docs, "w", encoding="utf-8") as f:
        f.write(serialized)
    print(f"Updated {args.docs}: rebuilt v2 API References group.")


if __name__ == "__main__":
    main()
