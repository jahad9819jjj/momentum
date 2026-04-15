// MomentumBridge.h
// C bridging header for Momentum C++ library → Swift
//
// Swift cannot directly call C++ (templates, STL, Eigen, etc.)
// so we expose a flat C API that wraps the key Momentum functions.

#ifndef MOMENTUM_BRIDGE_H
#define MOMENTUM_BRIDGE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// Opaque handle types
// ---------------------------------------------------------------------------
typedef struct MomentumCharacter_s* MomentumCharacter;
typedef struct MomentumSkeletonState_s* MomentumSkeletonState;

// ---------------------------------------------------------------------------
// 3-component vector / quaternion / transform (plain C structs)
// ---------------------------------------------------------------------------
typedef struct {
  float x, y, z;
} MBVec3;

typedef struct {
  float x, y, z, w; // Hamilton convention (x,y,z,w)
} MBQuat;

typedef struct {
  MBQuat rotation;
  MBVec3 translation;
  float scale;
} MBTransform;

// ---------------------------------------------------------------------------
// Character loading / lifetime
// ---------------------------------------------------------------------------

/// Load a character from a file (.glb or .fbx).
/// Returns NULL on failure.
MomentumCharacter mb_character_load(const char* path);

/// Destroy a loaded character.
void mb_character_destroy(MomentumCharacter ch);

/// Get the number of joints.
int32_t mb_character_num_joints(MomentumCharacter ch);

/// Get the number of model parameters.
int32_t mb_character_num_model_params(MomentumCharacter ch);

/// Get the name of a joint by index. Returns NULL if out of range.
/// The returned pointer is valid until the character is destroyed.
const char* mb_character_joint_name(MomentumCharacter ch, int32_t jointIndex);

/// Get the parent index of a joint. Returns -1 for root joints.
int32_t mb_character_joint_parent(MomentumCharacter ch, int32_t jointIndex);

/// Find a joint index by name. Returns -1 if not found.
int32_t mb_character_find_joint(MomentumCharacter ch, const char* name);

/// Get a model parameter name by index.
const char* mb_character_param_name(MomentumCharacter ch, int32_t paramIndex);

// ---------------------------------------------------------------------------
// Forward Kinematics
// ---------------------------------------------------------------------------

/// Compute forward kinematics from model parameters.
/// `modelParams` must have mb_character_num_model_params() elements.
/// Returns a new skeleton state handle (caller must destroy).
MomentumSkeletonState mb_fk_from_model_params(
    MomentumCharacter ch,
    const float* modelParams,
    int32_t numParams);

/// Compute forward kinematics from joint parameters.
/// `jointParams` must have (numJoints * 7) elements.
/// Returns a new skeleton state handle (caller must destroy).
MomentumSkeletonState mb_fk_from_joint_params(
    MomentumCharacter ch,
    const float* jointParams,
    int32_t numJointParams);

/// Compute forward kinematics at bind (rest) pose.
MomentumSkeletonState mb_fk_bind_pose(MomentumCharacter ch);

/// Destroy a skeleton state.
void mb_skeleton_state_destroy(MomentumSkeletonState state);

/// Get the world-space transform of a joint.
MBTransform mb_skeleton_state_joint_transform(
    MomentumSkeletonState state,
    int32_t jointIndex);

/// Get all joint world-space transforms at once.
/// `outTransforms` must have room for numJoints elements.
void mb_skeleton_state_all_transforms(
    MomentumSkeletonState state,
    MBTransform* outTransforms,
    int32_t maxJoints);

/// Get the world-space position of a joint.
MBVec3 mb_skeleton_state_joint_position(
    MomentumSkeletonState state,
    int32_t jointIndex);

// ---------------------------------------------------------------------------
// Character saving
// ---------------------------------------------------------------------------

/// Save a character (with optional motion) to a file.
/// `motion` can be NULL if numFrames == 0.
/// motionData layout: numModelParams x numFrames (column-major).
/// Returns true on success.
bool mb_character_save(
    MomentumCharacter ch,
    const char* path,
    float fps,
    const float* motionData,
    int32_t numModelParams,
    int32_t numFrames);

#ifdef __cplusplus
} // extern "C"
#endif

#endif // MOMENTUM_BRIDGE_H
