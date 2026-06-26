# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-26

### Added

- Native **Swift/SwiftUI** rewrite shipping in three editions from one codebase —
  **Direct download, Setapp, and the Mac App Store** (`apple/`).
- UI-free `SeshatCore` package (config, state, transcript cleaning, validation,
  prompt, WhisperX/Ollama clients, AVFoundation audio conversion, pipeline) with
  a headless `swift test` suite.
- **"Report an Issue…"** menu item that opens a pre-filled GitHub issue with
  non-sensitive diagnostics (version, edition, macOS, hardware).
- Release automation: tag-triggered Developer ID notarized DMG → GitHub Release,
  and App Store Connect upload (`.github/workflows/release*.yml`).

### Changed

- Renamed the product to **Seshat**.
- Audio conversion uses **AVFoundation** instead of `ffmpeg` (no GPL dependency,
  which is what makes App Store distribution possible).
- Native Settings window replaces the localhost settings web page.

### Removed

- The original Python implementation (kept in git history as the behavioural spec).

## [0.1.0] - 2026-06-24

### Added

- Initial release: a macOS menu-bar app that watches a folder for new audio/video
  recordings.
- Automatic pipeline: local conversion to WAV → transcription on a
  user-configured **WhisperX** server → summarisation with a user-configured
  **Ollama** model → validation → Markdown note written to the notes folder.
- Settings page for configuring servers, folders, and the watch interval, with a
  **Test connection** button.
- Menu actions: Process now, Copy last transcript, Open last note, Watch
  interval, Use local Ollama, open folders, Settings…, Pause/Resume, Quit.
- Headless CLI to process all pending recordings once.

[Unreleased]: https://github.com/joanmarcriera/seshat/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/joanmarcriera/seshat/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/joanmarcriera/seshat/releases/tag/v0.1.0
