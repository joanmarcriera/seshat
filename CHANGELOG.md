# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-24

### Added

- Initial release of **Scribed**.
- macOS menu-bar app that watches a folder for new audio/video recordings.
- Automatic pipeline: local `ffmpeg` conversion to WAV → transcription on a
  user-configured **WhisperX** server → summarisation with a user-configured
  **Ollama** model → validation → Markdown note written to the notes folder.
- Localhost **settings web page** (CSRF token + Host check, bound to
  `127.0.0.1`) for configuring servers, folders, and the watch interval, with a
  **Test connection** button.
- Menu actions: Process now, Copy last transcript, Open last note, Watch
  interval, Use local Ollama, open folders, Settings…, Pause/Resume, Quit.
- Headless CLI (`scribed`) to process all pending recordings once.
- `install-login-item.sh` to run the app at login (and `--uninstall` to stop).

[Unreleased]: https://github.com/Joanmarcriera/scribed/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Joanmarcriera/scribed/releases/tag/v0.1.0
