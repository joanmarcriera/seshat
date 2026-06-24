# Scribed

![CI](https://github.com/Joanmarcriera/scribed/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

> Drop a recording in a folder, get a tidy Markdown meeting note back.

**Scribed** is a macOS menu-bar app that watches a folder for audio/video
recordings and automatically turns each new one into a structured Markdown
meeting note. It converts the file locally with `ffmpeg`, transcribes it on
**your own WhisperX server**, summarises the transcript with **your own Ollama
server**, validates the result, and writes a note to your notes folder.

Scribed does not bundle any AI servers — you point it at WhisperX and Ollama
endpoints that you run and trust. **macOS only.**

## Screenshots

<!-- TODO: add a menu-bar screenshot / demo GIF -->

## Requirements / Prerequisites

- **macOS** (this is a menu-bar app built on `rumps`/AppKit — macOS only).
- **[ffmpeg](https://ffmpeg.org/)** on your `PATH` — install with Homebrew:
  `brew install ffmpeg`.
- **[uv](https://docs.astral.sh/uv/)** to manage the Python environment and run
  the app.
- **A reachable WhisperX HTTP endpoint** that you run — see
  [WhisperX](https://github.com/m-bain/whisperX).
- **A reachable Ollama HTTP endpoint** with a model pulled (for example
  `llama3.1:8b`) — see [Ollama](https://ollama.com).

These servers can be on `localhost`, on another machine on your network, or
anywhere you can reach — Scribed never starts them for you, and only ever talks
to the URLs you configure.

## Install

```sh
# from the project directory
uv sync
```

To run Scribed automatically at every login, install the LaunchAgent:

```sh
./install-login-item.sh
```

This starts the menu-bar app now and on every login. To stop and remove it:

```sh
./install-login-item.sh --uninstall
```

## Configure

On first run, Scribed opens its **Settings** page in your browser
automatically. You can reopen it any time from the menu (**Settings…**).

In Settings, fill in:

- your **WhisperX URL** (and model, language, speaker options),
- your **Ollama URL and model** for summarisation,
- the watch / notes / work folders if you want non-default locations.

Use the **Test connection** button to confirm Scribed can reach WhisperX and
Ollama before you drop in a recording. The Settings page is served on
`127.0.0.1` only.

## How it works

1. Scribed watches the **recordings folder** (default
   `~/Documents/MeetingNotes/recordings`) on a configurable interval.
2. When a new recording appears, `ffmpeg` converts it locally to WAV.
3. The WAV is uploaded to your configured **WhisperX** server for
   transcription.
4. The cleaned transcript is sent to your configured **Ollama** model for
   summarisation.
5. The summary is validated and written as Markdown to the **notes folder**
   (default `~/Documents/MeetingNotes/notes/<name>.md`).

Config and the work/cache directory live under
`~/Library/Application Support/MeetingNotes/`, and logs are written to
`~/Library/Logs/MeetingNotes/watcher.log`.

Supported input formats include `.wav`, `.m4a`, `.mp3`, `.opus`, `.ogg`,
`.flac`, `.aac`, `.m4b`, `.mov`, `.mp4`, `.m4v`, `.3gp`, `.webm`, and `.mkv`.

## Menu reference

| Item | What it does |
| --- | --- |
| *(status line)* | Shows the current state (Idle, Processing…, last note, etc.). |
| **Process now** | Clears failed/stale markers and processes all pending recordings immediately. |
| **Copy last transcript** | Copies the most recent transcript to the clipboard. |
| **Open last note** | Opens the most recently written Markdown note. |
| **Watch interval** | Choose how often the folder is scanned (10s / 20s / 60s / 5m). |
| **Use local Ollama (loads Mac)** | Toggle allowing the local Ollama fallback when the server is offline. |
| **Open meeting-notes folder** | Reveals the notes folder in Finder. |
| **Open recordings folder** | Reveals the watched recordings folder in Finder. |
| **Settings…** | Opens the localhost settings page. |
| **Pause / Resume watching** | Stops/starts automatic scanning. |
| **Quit** | Stops the settings server and quits the app. |

## Headless usage

To process every pending recording once without the GUI (useful for testing or
cron):

```sh
uv run scribed
```

It reads the same config and exits non-zero if any recording failed or was
deferred. You can override folders with `--recordings-dir`, `--notes-dir`, and
`--work-dir`, or point at a different config with `--config`.

## Privacy

Scribed is built to keep your data on machines you control:

- Audio is converted to WAV **locally** with `ffmpeg`.
- The WAV is uploaded **only** to the WhisperX server you configured, and the
  transcript is sent **only** to the Ollama server you configured. These may be
  remote, so **point Scribed only at servers you trust.**
- Notes and transcripts are written in **cleartext** under your home directory.
- **There is no telemetry and no phone-home.** Nothing is sent anywhere except
  the WhisperX/Ollama endpoints you set.

See [PRIVACY.md](PRIVACY.md) for the full statement.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Roadmap

Planned direction (GitHub → Homebrew → Setapp) is described in
[ROADMAP.md](ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).

## Support / Buy Me a Coffee

If Scribed saves you time, you can support its development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/TODO-username)

> Maintainer: replace `TODO-username` with your real Buy Me a Coffee username
> (here and in `.github/FUNDING.yml`).
