#!/usr/bin/env python3
"""Headless entry point shim — see meeting_pipeline.cli for the logic."""

from meeting_pipeline.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
