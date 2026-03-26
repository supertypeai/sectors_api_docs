#!/usr/bin/env python3
"""
generate_mdx_stubs.py

Reads schema.json produced by `python manage.py spectacular --file schema.json`
and creates/updates Mintlify MDX stub files for every operation that carries
an `x-mdx-path` extension.

Each stub contains only YAML frontmatter:

    ---
    title: "<operation summary>"
    openapi: "<METHOD> <path>"
    ---

Mintlify renders the full page (parameters, examples, response schemas) from
the OpenAPI spec automatically; the stub is just a pointer.

For existing files that still use the legacy `api:` format (hand-written MDX),
only the `title:` field is updated; the rest of the file is left intact so
hand-written content is not lost.

Usage:
    python scripts/generate_mdx_stubs.py \\
        --schema schema.json \\
        --mintlify-root mintlify

    # Dry-run (print what would change, no writes):
    python scripts/generate_mdx_stubs.py --schema schema.json --dry-run
"""

import argparse
import json
import os
import re
import sys

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
FIELD_RE = re.compile(r"^(?P<key>\w[\w-]*):\s*(?P<value>.+)$", re.MULTILINE)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (fields_dict, body_after_frontmatter). fields_dict is empty if no frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fields = {}
    for fm in FIELD_RE.finditer(m.group(1)):
        fields[fm.group("key")] = fm.group("value").strip('"').strip("'")
    body = text[m.end() :]
    return fields, body


def render_frontmatter(fields: dict) -> str:
    lines = []
    for k, v in fields.items():
        # Quote values that contain colons or leading/trailing spaces
        if ":" in v or v != v.strip():
            v = f'"{v}"'
        lines.append(f"{k}: {v}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def collect_operations(schema: dict) -> list[dict]:
    """Return list of {method, path, summary, x_mdx_path} for ops with x-mdx-path."""
    ops = []
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            mdx_path = operation.get("x-mdx-path")
            if not mdx_path:
                continue
            ops.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": operation.get("summary", ""),
                    "x_mdx_path": mdx_path,
                }
            )
    return ops


def process_file(
    mdx_file: str,
    title: str,
    openapi: str,
    dry_run: bool,
) -> str:
    """
    Create or update mdx_file.
    Returns a short action string: "created", "updated-title", "updated-openapi", "ok".
    """
    if os.path.exists(mdx_file):
        with open(mdx_file, encoding="utf-8") as f:
            content = f.read()
        fields, body = parse_frontmatter(content)

        changed = False
        action_parts = []

        # Always sync the title
        if fields.get("title") != title:
            fields["title"] = title
            changed = True
            action_parts.append("title")

        if "openapi" in fields:
            # New-format file: sync openapi too
            if fields["openapi"] != openapi:
                fields["openapi"] = openapi
                changed = True
                action_parts.append("openapi")
        # Legacy `api:` files: leave the api field alone, only title was synced

        if not changed:
            return "ok"

        new_content = render_frontmatter(fields) + body
        action = "updated(" + ",".join(action_parts) + ")"
    else:
        # Create new stub
        fields = {"title": title, "openapi": openapi}
        new_content = render_frontmatter(fields) + "\n"
        action = "created"

    if not dry_run:
        os.makedirs(os.path.dirname(mdx_file), exist_ok=True)
        with open(mdx_file, "w", encoding="utf-8") as f:
            f.write(new_content)

    return action


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--schema",
        default="schema.json",
        help="Path to schema.json (default: schema.json)",
    )
    parser.add_argument(
        "--mintlify-root",
        default="mintlify",
        help="Root directory of the Mintlify project (default: mintlify)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files",
    )
    args = parser.parse_args()

    if not os.path.exists(args.schema):
        print(f"ERROR: schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(1)

    with open(args.schema, encoding="utf-8") as f:
        schema = json.load(f)

    ops = collect_operations(schema)
    if not ops:
        print("No operations with x-mdx-path found in schema.", file=sys.stderr)
        sys.exit(1)

    counts = {"created": 0, "updated": 0, "ok": 0}
    for op in ops:
        mdx_rel = op["x_mdx_path"] + ".mdx"
        mdx_file = os.path.join(args.mintlify_root, mdx_rel)
        openapi_val = f"{op['method']} {op['path']}"
        action = process_file(mdx_file, op["summary"], openapi_val, args.dry_run)

        prefix = "[dry-run] " if args.dry_run else ""
        if action == "ok":
            counts["ok"] += 1
        elif action == "created":
            counts["created"] += 1
            print(f"{prefix}CREATED  {mdx_rel}")
        else:
            counts["updated"] += 1
            print(f"{prefix}UPDATED  {mdx_rel}  ({action})")

    total = len(ops)
    print(
        f"\n{'[dry-run] ' if args.dry_run else ''}"
        f"{total} endpoints processed: "
        f"{counts['created']} created, "
        f"{counts['updated']} updated, "
        f"{counts['ok']} already in sync."
    )


if __name__ == "__main__":
    main()
