// swift-tools-version:5.9
import PackageDescription

// UI-free core of Scribed: config, state, transcript cleaning, validation, and
// the summarisation prompt — ported from the Python `meeting_pipeline` package
// and verified against it with parity tests (`swift test`). The macOS app links
// this package; AppKit/AVFoundation/SwiftUI stay in the app target.
let package = Package(
    name: "ScribedCore",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "ScribedCore", targets: ["ScribedCore"]),
    ],
    targets: [
        .target(name: "ScribedCore"),
        .testTarget(
            name: "ScribedCoreTests",
            dependencies: ["ScribedCore"],
            resources: [.process("Fixtures")]
        ),
    ]
)
