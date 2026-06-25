import Foundation
import ScribedCore

/// Skeleton of the menu-bar controller. Mirrors the Python `WatcherController`
/// (status line, pause, interval, local-Ollama toggle, manual actions). Config is
/// loaded from ScribedCore; the real scan loop + pipeline land later in Phase C.
@MainActor
final class WatcherController: ObservableObject {
    @Published private(set) var status: String = "Idle"
    @Published var isPaused: Bool = false
    @Published var allowLocalOllama: Bool
    @Published private(set) var watchIntervalSeconds: Int

    private(set) var config: Config

    static let intervalChoices: [Int] = [10, 20, 60, 300]

    init() {
        var cfg = (try? Config.load(from: Config.defaultConfigURL)) ?? Config()
        cfg.applyEnvOverrides()
        self.config = cfg
        self.watchIntervalSeconds = cfg.watchIntervalSeconds
        self.allowLocalOllama = cfg.summarise.allowLocalFallback
    }

    // MARK: Manual actions (Phase C wires these to the real pipeline)

    func processNow() { status = "Processing…" }
    func scanOnce() {}
    func copyLastTranscript() {}
    func openLastNote() {}
    func openNotesFolder() {}
    func openRecordingsFolder() {}

    // MARK: Settings toggles

    func setInterval(_ seconds: Int) { watchIntervalSeconds = seconds }

    func togglePause() {
        isPaused.toggle()
        status = isPaused ? "Paused" : "Idle"
    }

    func toggleAllowLocal() { allowLocalOllama.toggle() }
}
