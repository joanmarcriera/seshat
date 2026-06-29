#!/usr/bin/env python3
"""Bump Distavo's releasable version after a merge to main."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_YML = ROOT / "apple" / "project.yml"
SITE_INDEX = ROOT / "ops" / "site" / "index.html"
SETAPP_DOC = ROOT / "docs" / "setapp-submission.md"


@dataclass(frozen=True)
class VersionBump:
    old_marketing: str
    new_marketing: str
    old_build: int
    new_build: int


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"expected exactly one match for {label}, found {count}")
    return updated


def read_project_version() -> VersionBump:
    text = PROJECT_YML.read_text(encoding="utf-8")

    marketing_match = re.search(
        r'^\s*MARKETING_VERSION:\s*"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"\s*$',
        text,
        flags=re.MULTILINE,
    )
    if marketing_match is None:
        raise ValueError(f"could not find MARKETING_VERSION in {PROJECT_YML}")

    build_match = re.search(
        r'^\s*CURRENT_PROJECT_VERSION:\s*"(?P<build>\d+)"\s*$',
        text,
        flags=re.MULTILINE,
    )
    if build_match is None:
        raise ValueError(f"could not find CURRENT_PROJECT_VERSION in {PROJECT_YML}")

    major = int(marketing_match.group("major"))
    minor = int(marketing_match.group("minor"))
    old_marketing = (
        f"{marketing_match.group('major')}."
        f"{marketing_match.group('minor')}."
        f"{marketing_match.group('patch')}"
    )
    old_build = int(build_match.group("build"))

    return VersionBump(
        old_marketing=old_marketing,
        new_marketing=f"{major}.{minor + 1}.0",
        old_build=old_build,
        new_build=old_build + 1,
    )


def update_project_yml(bump: VersionBump) -> None:
    text = PROJECT_YML.read_text(encoding="utf-8")
    text = replace_once(
        text,
        r'^(\s*MARKETING_VERSION:\s*)"[^"]+"(\s*)$',
        rf'\1"{bump.new_marketing}"\2',
        "MARKETING_VERSION",
    )
    text = replace_once(
        text,
        r'^(\s*CURRENT_PROJECT_VERSION:\s*)"[^"]+"(\s*)$',
        rf'\1"{bump.new_build}"\2',
        "CURRENT_PROJECT_VERSION",
    )
    PROJECT_YML.write_text(text, encoding="utf-8")


def replace_old_version(path: Path, bump: VersionBump) -> None:
    text = path.read_text(encoding="utf-8")
    if bump.old_marketing not in text:
        return
    path.write_text(text.replace(bump.old_marketing, bump.new_marketing), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the computed bump without editing files.",
    )
    args = parser.parse_args()

    bump = read_project_version()
    print(f"OLD_MARKETING_VERSION={bump.old_marketing}")
    print(f"NEW_MARKETING_VERSION={bump.new_marketing}")
    print(f"OLD_BUILD_VERSION={bump.old_build}")
    print(f"NEW_BUILD_VERSION={bump.new_build}")

    if args.dry_run:
        return 0

    update_project_yml(bump)
    replace_old_version(SITE_INDEX, bump)
    replace_old_version(SETAPP_DOC, bump)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
