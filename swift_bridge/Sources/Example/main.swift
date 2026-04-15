// main.swift
// Example: Using Momentum from Swift

import Momentum

// 1. Load a character model
guard let character = Character(path: "path/to/character.glb") else {
    print("Error: Failed to load character model")
    exit(1)
}

print("Loaded character with \(character.numJoints) joints, \(character.numModelParameters) parameters")

// 2. Print skeleton hierarchy
print("\n--- Skeleton Hierarchy ---")
for joint in character.joints {
    let parentName: String
    if let parentIdx = joint.parentIndex {
        parentName = character.joint(at: parentIdx)?.name ?? "?"
    } else {
        parentName = "(root)"
    }
    print("  [\(joint.index)] \(joint.name)  parent: \(parentName)")
}

// 3. Compute forward kinematics at bind pose
print("\n--- Bind Pose Joint Positions ---")
if let state = character.bindPose() {
    for i in 0..<character.numJoints {
        let pos = state.jointPosition(at: i)
        let name = character.joint(at: i)?.name ?? "?"
        print("  \(name): (\(pos.x), \(pos.y), \(pos.z))")
    }
}

// 4. Compute forward kinematics with custom model parameters
print("\n--- Custom Pose ---")
var params = [Float](repeating: 0.0, count: character.numModelParameters)
// Set some parameters (e.g., a rotation) if you know the parameter names
// Find a specific parameter:
if let hipIdx = character.findJoint(named: "b_root") {
    print("Found hip joint at index \(hipIdx)")
}
// Print all parameter names
print("Parameter names: \(character.parameterNames.prefix(10))...")

if let state = character.forwardKinematics(modelParameters: params) {
    let transforms = state.allTransforms()
    print("Computed \(transforms.count) joint transforms")
    if let first = transforms.first {
        print("  Root: pos=(\(first.translation.x), \(first.translation.y), \(first.translation.z))")
    }
}

print("\nDone!")
