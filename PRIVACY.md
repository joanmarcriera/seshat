# Privacy

Scribed is designed so that your recordings and notes stay on machines you
control. This document describes exactly what data Scribed produces, where it is
stored, and what (if anything) leaves your Mac.

## What data Scribed produces

For each recording it processes, Scribed creates:

- **A WAV copy** of the recording, produced locally by `ffmpeg` from your
  original file.
- **A transcript** of the audio, returned by your WhisperX server.
- **A summary / structured note**, produced by your Ollama model from the
  transcript.
- The original recording file is left where you placed it.

## Where data is stored locally

- **Recordings** you drop in: the watched folder, by default
  `~/Documents/MeetingNotes/recordings`.
- **Notes** (the final Markdown): by default
  `~/Documents/MeetingNotes/notes/<name>.md`.
- **Working/cache files** (including intermediate WAVs and transcripts) and the
  app's configuration (`watcher-config.json`): under
  `~/Library/Application Support/MeetingNotes/`.
- **Logs**: `~/Library/Logs/MeetingNotes/watcher.log`.

All of these are written in **cleartext** under your home directory. Scribed
does not encrypt them; protect them with your normal macOS account and disk
encryption (FileVault).

## What leaves your machine, and where it goes

Scribed talks to exactly two network endpoints, both of which **you** configure:

1. **Your WhisperX server** — the locally converted WAV is uploaded here for
   transcription.
2. **Your Ollama server** — the cleaned transcript is sent here for
   summarisation, and the model's response comes back.

These endpoints can be on `localhost`, on your own network, or remote. Because
the audio and transcript leave your Mac to reach them, **only configure servers
you operate or fully trust.** If you want everything to stay on your own Mac,
run WhisperX and Ollama locally and point Scribed at `127.0.0.1`.

## No telemetry

Scribed has **no telemetry and no phone-home**. It does not collect analytics,
crash reports, usage statistics, or any other data, and it does not contact any
server other than the WhisperX and Ollama URLs you set. The settings web page is
bound to `127.0.0.1` only and is not reachable from the network.

## Recommendation

Prefer **local or otherwise trusted** WhisperX and Ollama servers. Treat the
configured URLs as the only places your meeting content travels, and review them
before processing sensitive recordings.
