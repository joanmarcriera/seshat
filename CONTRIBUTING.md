# Contributing to Scribed

Thanks for your interest in improving Scribed! This guide covers how to set up,
test, and submit changes. By participating you agree to follow our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Prerequisites

- macOS (the app itself is macOS-only)
- [uv](https://docs.astral.sh/uv/)
- `ffmpeg` on your `PATH` (`brew install ffmpeg`) for end-to-end runs

## Setup

```sh
uv sync --extra dev
```

This installs the project plus the `dev` extras (pytest).

## Running the tests

```sh
uv run pytest
```

The core pipeline is covered by unit tests under `tests/`. Please keep them
green.

### Test-driven development

We expect a **TDD** workflow: write or update a failing test that captures the
behaviour you want, then implement the change until it passes. New features and
bug fixes should come with tests. The `meeting_pipeline` core is deliberately
UI-free so it can be tested without launching the menu bar.

## Coding conventions

- **Small, focused modules.** Keep each module doing one thing.
- **Keep `meeting_pipeline` UI-free and testable.** No `rumps`/AppKit imports in
  the core pipeline — only `menubar_app.py` and the menu layer touch the UI.
- **Main-thread UI.** All `rumps`/AppKit menu mutation must happen on the main
  thread; background work (scanning, processing) runs on daemon threads and
  hands results back without mutating UI off-thread.
- Prefer pure functions for logic so they can be unit-tested directly (see how
  `settings_server.py` separates pure helpers from the HTTP server).

## Running the app locally

```sh
uv run python menubar_app.py
```

On first run it opens the Settings page so you can configure your WhisperX and
Ollama endpoints. You can also exercise the pipeline headlessly with:

```sh
uv run scribed
```

## Shell scripts

If you change `install-login-item.sh` (or any shell script), syntax-check it:

```sh
bash -n install-login-item.sh
```

CI runs this check too.

## Pull request process

1. Fork and create a feature branch.
2. Make your change with accompanying tests (TDD).
3. Ensure `uv run pytest` passes and `bash -n install-login-item.sh` is clean.
4. Update docs (`README.md`, etc.) if behaviour changed.
5. **Do not commit any private data** — no recordings, notes, transcripts,
   real server IPs, or tokens (see `.gitignore`).
6. Open a PR using the template; fill in the checklist.

We review for correctness, test coverage, and that the core stays UI-free and
main-thread-safe.
