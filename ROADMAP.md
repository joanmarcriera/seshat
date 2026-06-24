# Roadmap

Scribed's distribution plan moves from a source-based GitHub release toward
easy package-manager installs and, eventually, a notarized Mac app on Setapp.
Each phase is more involved than the last.

## Phase 1 — GitHub open-source release (current)

- Public GitHub repository under an MIT license.
- Run from source with `uv sync` and `./install-login-item.sh`.
- Documentation, CI, issue/PR templates, and contribution guidelines in place.

This is where the project is today.

## Phase 2 — Homebrew

Make Scribed installable with standard tooling.

- Ensure Scribed is cleanly **pip/uv-installable** — the `scribed` entry point
  is already defined in `pyproject.toml`.
- Ship a **Homebrew CLI formula** that declares `ffmpeg` as a dependency, so
  `brew install` brings the transcription prerequisite along.
- Later, provide an **`.app` cask** for users who prefer a downloadable app
  bundle over a CLI formula.

## Phase 3 — Setapp (the hard one)

Distributing through Setapp requires a real, sandboxed, notarized Mac app. This
is a substantial body of work:

- **Build a notarized `.app`** with `py2app`:
  - `LSUIElement=1` so it runs as a menu-bar-only agent (no Dock icon).
  - A proper app icon.
  - A **bundled, signed static `ffmpeg`** binary so users don't need Homebrew —
    note the licensing implications and use an **LGPL** ffmpeg build.
- **App Sandbox compliance**:
  - Replace arbitrary config-driven paths with **security-scoped bookmarks** for
    the watched folder.
  - Add the appropriate **network client/server entitlements** for talking to
    WhisperX/Ollama.
  - Replace the `LaunchAgent` plist with **`SMAppService`** for run-at-login.
  - Consider a **native settings window** instead of the localhost web server.
- **Code-sign** with the hardened runtime → **notarize** → **staple** the
  ticket.
- Integrate the **Setapp SDK** and go through Setapp's curated review.

### Naming note

The working name **"Scribed"** must be **trademark-checked** before any public
distribution, and a real **reverse-DNS bundle identifier** chosen (the current
`com.scribed.app` label in the LaunchAgent is a placeholder).
