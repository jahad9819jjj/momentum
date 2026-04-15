// Momentum.swift
// Swift wrapper around the MomentumBridge C API
// Provides a safe, idiomatic Swift interface.

import CMomentum
import Foundation

// MARK: - Value Types

/// 3D vector
public struct Vec3 {
    public var x: Float
    public var y: Float
    public var z: Float

    public init(x: Float = 0, y: Float = 0, z: Float = 0) {
        self.x = x; self.y = y; self.z = z
    }

    init(_ v: MBVec3) {
        self.x = v.x; self.y = v.y; self.z = v.z
    }
}

/// Quaternion (x, y, z, w)
public struct Quat {
    public var x: Float
    public var y: Float
    public var z: Float
    public var w: Float

    public init(x: Float = 0, y: Float = 0, z: Float = 0, w: Float = 1) {
        self.x = x; self.y = y; self.z = z; self.w = w
    }

    init(_ q: MBQuat) {
        self.x = q.x; self.y = q.y; self.z = q.z; self.w = q.w
    }
}

/// Rigid body transform with uniform scale
public struct Transform {
    public var rotation: Quat
    public var translation: Vec3
    public var scale: Float

    public init(
        rotation: Quat = Quat(),
        translation: Vec3 = Vec3(),
        scale: Float = 1.0
    ) {
        self.rotation = rotation
        self.translation = translation
        self.scale = scale
    }

    init(_ t: MBTransform) {
        self.rotation = Quat(t.rotation)
        self.translation = Vec3(t.translation)
        self.scale = t.scale
    }
}

// MARK: - Joint Info

/// Information about a single joint in the skeleton
public struct JointInfo {
    public let index: Int
    public let name: String
    public let parentIndex: Int? // nil for root joints
}

// MARK: - Skeleton State

/// Result of forward kinematics computation
public class SkeletonState {
    let handle: MomentumSkeletonState
    public let numJoints: Int

    init(handle: MomentumSkeletonState, numJoints: Int) {
        self.handle = handle
        self.numJoints = numJoints
    }

    deinit {
        mb_skeleton_state_destroy(handle)
    }

    /// Get the world-space transform of a joint
    public func jointTransform(at index: Int) -> Transform {
        let t = mb_skeleton_state_joint_transform(handle, Int32(index))
        return Transform(t)
    }

    /// Get the world-space position of a joint
    public func jointPosition(at index: Int) -> Vec3 {
        let v = mb_skeleton_state_joint_position(handle, Int32(index))
        return Vec3(v)
    }

    /// Get all joint transforms
    public func allTransforms() -> [Transform] {
        var buf = [MBTransform](
            repeating: MBTransform(
                rotation: MBQuat(x: 0, y: 0, z: 0, w: 1),
                translation: MBVec3(x: 0, y: 0, z: 0),
                scale: 1.0
            ),
            count: numJoints
        )
        mb_skeleton_state_all_transforms(handle, &buf, Int32(numJoints))
        return buf.map { Transform($0) }
    }
}

// MARK: - Character

/// A Momentum character model loaded from a file
public class Character {
    let handle: MomentumCharacter

    /// Load a character from a .glb or .fbx file
    public init?(path: String) {
        guard let h = mb_character_load(path) else {
            return nil
        }
        self.handle = h
    }

    deinit {
        mb_character_destroy(handle)
    }

    /// Number of joints in the skeleton
    public var numJoints: Int {
        Int(mb_character_num_joints(handle))
    }

    /// Number of model parameters
    public var numModelParameters: Int {
        Int(mb_character_num_model_params(handle))
    }

    /// Get joint information
    public func joint(at index: Int) -> JointInfo? {
        guard index >= 0 && index < numJoints else { return nil }
        guard let namePtr = mb_character_joint_name(handle, Int32(index)) else {
            return nil
        }
        let parentIdx = mb_character_joint_parent(handle, Int32(index))
        return JointInfo(
            index: index,
            name: String(cString: namePtr),
            parentIndex: parentIdx >= 0 ? Int(parentIdx) : nil
        )
    }

    /// Get all joint infos
    public var joints: [JointInfo] {
        (0..<numJoints).compactMap { joint(at: $0) }
    }

    /// Find a joint by name
    public func findJoint(named name: String) -> Int? {
        let idx = mb_character_find_joint(handle, name)
        return idx >= 0 ? Int(idx) : nil
    }

    /// Get the name of a model parameter
    public func parameterName(at index: Int) -> String? {
        guard let ptr = mb_character_param_name(handle, Int32(index)) else {
            return nil
        }
        return String(cString: ptr)
    }

    /// All model parameter names
    public var parameterNames: [String] {
        (0..<numModelParameters).compactMap { parameterName(at: $0) }
    }

    // MARK: Forward Kinematics

    /// Compute FK from model parameters
    public func forwardKinematics(modelParameters: [Float]) -> SkeletonState? {
        guard modelParameters.count == numModelParameters else { return nil }
        guard let h = mb_fk_from_model_params(
            handle,
            modelParameters,
            Int32(modelParameters.count)
        ) else {
            return nil
        }
        return SkeletonState(handle: h, numJoints: numJoints)
    }

    /// Compute FK from joint parameters (7 per joint: tx,ty,tz,rx,ry,rz,scale)
    public func forwardKinematics(jointParameters: [Float]) -> SkeletonState? {
        guard jointParameters.count == numJoints * 7 else { return nil }
        guard let h = mb_fk_from_joint_params(
            handle,
            jointParameters,
            Int32(jointParameters.count)
        ) else {
            return nil
        }
        return SkeletonState(handle: h, numJoints: numJoints)
    }

    /// Compute FK at bind (rest) pose
    public func bindPose() -> SkeletonState? {
        guard let h = mb_fk_bind_pose(handle) else { return nil }
        return SkeletonState(handle: h, numJoints: numJoints)
    }

    // MARK: Saving

    /// Save character to file (.glb, .fbx, etc.)
    public func save(to path: String, fps: Float = 120.0) -> Bool {
        return mb_character_save(handle, path, fps, nil, 0, 0)
    }
}
