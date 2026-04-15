// swift-tools-version:5.9
import PackageDescription

// Paths must be adjusted to match your build environment.
// See README_SWIFT.md for setup instructions.

let package = Package(
    name: "MomentumSwift",
    products: [
        .library(name: "Momentum", targets: ["Momentum"]),
        .executable(name: "MomentumExample", targets: ["Example"]),
    ],
    targets: [
        // System module wrapping the C bridge library
        .systemLibrary(
            name: "CMomentum",
            path: ".",  // Contains module.modulemap and MomentumBridge.h
            pkgConfig: nil,
            providers: []
        ),
        // Swift wrapper library
        .target(
            name: "Momentum",
            dependencies: ["CMomentum"],
            path: "Sources/Momentum"
        ),
        // Example executable
        .executableTarget(
            name: "Example",
            dependencies: ["Momentum"],
            path: "Sources/Example"
        ),
    ]
)
