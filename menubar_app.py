#!/usr/bin/env python3
"""macOS menu-bar app: watch recordings/ and turn new files into meeting notes."""

from __future__ import annotations

import copy
import subprocess
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from meeting_pipeline import pipeline as pipe  # noqa: E402
from meeting_pipeline.config import load_config, resolve_path, save_config  # noqa: E402
from meeting_pipeline.settings_server import SettingsServer  # noqa: E402
from meeting_pipeline.state import State, iter_pending  # noqa: E402

CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "Scribed"
    / "watcher-config.json"
)


class WatcherController:
    def __init__(self, cfg, config_path, *, process_one=None, notify=None):
        self.cfg = cfg
        self.config_path = Path(config_path)
        self._process_one = process_one or pipe.process_one
        self._notify = notify or (lambda title, msg: None)
        self._lock = threading.Lock()
        self._scan_lock = threading.Lock()
        self._deferred: set[str] = set()
        self.status = "Idle"
        self.last_done = None
        # Nothing is running at startup, so any leftover .processing markers are
        # stale (a previous crash mid-process). Clear them so those recordings
        # become pending again instead of being stuck forever.
        self.clear_stale_processing()

    # --- core ---

    def _state(self, cfg):
        work_dir = resolve_path(cfg["work_dir"])
        notes_dir = resolve_path(cfg["notes_dir"])
        return State(work_dir / ".state", notes_dir)

    def clear_stale_processing(self) -> None:
        """Remove all *.processing markers (call only when nothing is running)."""
        with self._lock:
            state = self._state(self.cfg)
            for marker in state.state_dir.glob("*.processing"):
                marker.unlink(missing_ok=True)

    def scan_once(self):
        """Process all pending recordings (skips failed ones — they need retry_failed).

        Self-serializing: if a scan is already running, returns [] immediately so
        overlapping timer ticks / 'Process now' can't double-process a recording.
        """
        if not self._scan_lock.acquire(blocking=False):
            return []
        try:
            with self._lock:
                cfg = self.cfg
                recordings_dir = resolve_path(cfg["recordings_dir"])
                work_dir = resolve_path(cfg["work_dir"])
                notes_dir = resolve_path(cfg["notes_dir"])
                state = State(work_dir / ".state", notes_dir)
                pending = iter_pending(recordings_dir, state, pipe.SUPPORTED_EXTENSIONS)

            results = []
            for path in pending:
                self.status = f"Processing {path.name}…"
                self._notify("Meeting notes", f"Processing {path.name}…")
                result = self._process_one(path, cfg)
                results.append(result)
                self._handle_result(result)
            if not pending:
                self.status = "Idle"
            return results
        finally:
            self._scan_lock.release()

    def retry_failed(self):
        """Clear all .failed and stale .processing markers then scan.

        Used by the 'Process now' menu item.
        """
        with self._lock:
            state = self._state(self.cfg)
            for failed_marker in state.state_dir.glob("*.failed"):
                state.clear_failed(failed_marker.stem)
            for proc_marker in state.state_dir.glob("*.processing"):
                proc_marker.unlink(missing_ok=True)
        return self.scan_once()

    def _handle_result(self, result):
        if result.status == "done":
            self.status = f"Last note: {result.base}"
            self._deferred.discard(result.base)
            self.last_done = {
                "base": result.base,
                "note_path": result.note_path,
                "transcript_path": result.transcript_path,
            }
            self._notify("✅ Transcribed & summarised",
                         f"{result.base} — note ready. 'Copy last transcript' in the menu.")
        elif result.status == "deferred_need_local":
            self.status = "Needs local Ollama"
            # Only notify on transition INTO the deferred set, not every tick.
            if result.base not in self._deferred:
                self._deferred.add(result.base)
                self._notify(
                    "Server Ollama offline",
                    f"Enable 'Use local Ollama' to process {result.base} (loads this Mac).")
        elif result.status == "failed":
            self.status = f"Failed: {result.base}"
            self._notify("Processing failed", f"{result.base}: {result.message}")

    def last_transcript_text(self):
        if not self.last_done:
            return None
        tp = self.last_done.get("transcript_path")
        if tp and Path(tp).exists():
            return Path(tp).read_text(encoding="utf-8")
        return None

    def last_note_path(self):
        return self.last_done.get("note_path") if self.last_done else None

    # --- settings ---

    def has_deferred(self) -> bool:
        return bool(self._deferred)

    def deferred_bases(self):
        return sorted(self._deferred)

    def set_allow_local(self, value: bool) -> None:
        with self._lock:
            new_cfg = copy.deepcopy(self.cfg)
            new_cfg["summarise"]["allow_local_fallback"] = bool(value)
            self.cfg = new_cfg
            save_config(self.config_path, new_cfg)
            if value:
                self._deferred.clear()

    def apply_config(self, new_cfg: dict) -> None:
        """Persist and apply a full new config (used by the settings page)."""
        with self._lock:
            was_allowed = self.cfg["summarise"].get("allow_local_fallback")
            self.cfg = new_cfg
            save_config(self.config_path, new_cfg)
            if new_cfg["summarise"].get("allow_local_fallback") and not was_allowed:
                self._deferred.clear()

    def set_interval(self, seconds: int) -> None:
        with self._lock:
            new_cfg = copy.deepcopy(self.cfg)
            new_cfg["watch_interval_seconds"] = int(seconds)
            self.cfg = new_cfg
            save_config(self.config_path, new_cfg)

    def reload_config(self) -> None:
        self.cfg = load_config(self.config_path)


def main() -> int:
    import rumps

    # Detect first run BEFORE load_config writes the default file.
    first_run = not CONFIG_PATH.exists()
    cfg = load_config(CONFIG_PATH)

    class ScribedApp(rumps.App):
        def __init__(self):
            super().__init__("📝", quit_button=None)
            self.controller = WatcherController(
                cfg, CONFIG_PATH, notify=self._notify)
            self.settings_server = SettingsServer(
                lambda: self.controller.cfg, self.controller.apply_config)
            self.settings_server.start()
            self.paused = False
            self.status_item = rumps.MenuItem("Idle")
            self.status_item.set_callback(None)
            self.allow_local_item = rumps.MenuItem(
                "Use local Ollama (loads Mac)", callback=self._toggle_local)
            self.allow_local_item.state = bool(
                cfg["summarise"].get("allow_local_fallback"))
            interval_menu = rumps.MenuItem("Watch interval")
            for label, secs in [("10s", 10), ("20s", 20), ("60s", 60), ("5m", 300)]:
                interval_menu.add(rumps.MenuItem(
                    label, callback=self._make_interval_setter(secs)))
            self.menu = [
                self.status_item,
                None,
                rumps.MenuItem("Process now", callback=self._process_now),
                rumps.MenuItem("Copy last transcript", callback=self._copy_transcript),
                rumps.MenuItem("Open last note", callback=self._open_last_note),
                interval_menu,
                self.allow_local_item,
                None,
                rumps.MenuItem("Open meeting-notes folder", callback=self._open_notes),
                rumps.MenuItem("Open recordings folder", callback=self._open_recordings),
                rumps.MenuItem("Settings…", callback=self._open_settings),
                None,
                rumps.MenuItem("Pause watching", callback=self._toggle_pause),
                rumps.MenuItem("Quit", callback=self._quit),
            ]
            self.timer = rumps.Timer(self._tick, cfg["watch_interval_seconds"])
            self.timer.start()
            self.reconciler = rumps.Timer(self._reconcile, 2)
            self.reconciler.start()
            if first_run:
                self._open_settings_on_first_run()

        def _open_settings_on_first_run(self):
            """On first launch, open Settings so the user can configure servers.

            Wrapped so a failure here never crashes app startup.
            """
            try:
                subprocess.run(["open", self.settings_server.url])
                self._notify(
                    "Welcome",
                    "Configure your transcription & summary servers to begin.")
            except Exception:
                pass

        def _reconcile(self, _timer):
            cfg = self.controller.cfg
            desired = cfg["watch_interval_seconds"]
            if self.timer.interval != desired:
                self.timer.stop()
                self.timer.interval = desired
                self.timer.start()
            self.allow_local_item.state = bool(
                cfg["summarise"].get("allow_local_fallback"))
            if not self.paused:
                self.status_item.title = self.controller.status

        def _notify(self, title, message):
            try:
                rumps.notification(title, "", message)
            except Exception:
                pass

        def _tick(self, _timer):
            if self.paused:
                return
            threading.Thread(target=self._scan, daemon=True).start()

        def _scan(self):
            self.controller.scan_once()

        def _process_now(self, _):
            """Manual 'Process now' clears failed markers so every file gets a retry."""
            threading.Thread(target=self._retry_and_scan, daemon=True).start()

        def _retry_and_scan(self):
            self.controller.retry_failed()

        def _copy_transcript(self, _):
            text = self.controller.last_transcript_text()
            if not text:
                self._notify("No transcript yet", "Process a recording first.")
                return
            subprocess.run(["pbcopy"], input=text, text=True)
            base = self.controller.last_done.get("base", "")
            self._notify("Transcript copied", f"{base} is on the clipboard.")

        def _open_last_note(self, _):
            note = self.controller.last_note_path()
            if note and Path(note).exists():
                subprocess.run(["open", str(note)])
            else:
                self._notify("No note yet", "Process a recording first.")

        def _toggle_local(self, sender):
            sender.state = not sender.state
            self.controller.set_allow_local(bool(sender.state))
            if sender.state:
                threading.Thread(target=self._scan, daemon=True).start()

        def _make_interval_setter(self, secs):
            def setter(_):
                self.controller.set_interval(secs)
            return setter

        def _toggle_pause(self, sender):
            self.paused = not self.paused
            sender.title = "Resume watching" if self.paused else "Pause watching"
            self.status_item.title = "Paused" if self.paused else self.controller.status

        def _open_notes(self, _):
            subprocess.run(["open", str(
                resolve_path(self.controller.cfg["notes_dir"]))])

        def _open_recordings(self, _):
            subprocess.run(["open", str(
                resolve_path(self.controller.cfg["recordings_dir"]))])

        def _open_settings(self, _):
            subprocess.run(["open", self.settings_server.url])

        def _quit(self, _):
            try:
                self.settings_server.stop()
            except Exception:
                pass
            rumps.quit_application()

    ScribedApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
