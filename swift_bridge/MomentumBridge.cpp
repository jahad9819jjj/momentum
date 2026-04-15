// MomentumBridge.cpp
// Implementation of the C bridging layer for Momentum → Swift

#include "MomentumBridge.h"

#include <momentum/character/character.h>
#include <momentum/character/parameter_transform.h>
#include <momentum/character/skeleton.h>
#include <momentum/character/skeleton_state.h>
#include <momentum/io/character_io.h>
#include <momentum/math/transform.h>

#include <cstring>
#include <string>
#include <vector>

using namespace momentum;

// ---------------------------------------------------------------------------
// Internal wrapper structs (hidden behind opaque C handles)
// ---------------------------------------------------------------------------

struct MomentumCharacter_s {
  Character character;
  // Keep joint names alive so we can return const char* safely
  std::vector<std::string> jointNameCache;
  std::vector<std::string> paramNameCache;

  void buildCaches() {
    jointNameCache.clear();
    for (const auto& j : character.skeleton.joints) {
      jointNameCache.push_back(j.name);
    }
    paramNameCache.clear();
    for (const auto& n : character.parameterTransform.name) {
      paramNameCache.push_back(n);
    }
  }
};

struct MomentumSkeletonState_s {
  SkeletonState state;
  int32_t numJoints;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static MBVec3 toMBVec3(const Eigen::Vector3f& v) {
  return {v.x(), v.y(), v.z()};
}

static MBQuat toMBQuat(const Eigen::Quaternionf& q) {
  return {q.x(), q.y(), q.z(), q.w()};
}

static MBTransform toMBTransform(const TransformT<float>& t) {
  MBTransform r;
  r.rotation = toMBQuat(t.rotation);
  r.translation = toMBVec3(t.translation);
  r.scale = t.scale;
  return r;
}

// ---------------------------------------------------------------------------
// Character loading / lifetime
// ---------------------------------------------------------------------------

MomentumCharacter mb_character_load(const char* path) {
  if (!path) {
    return nullptr;
  }
  try {
    auto* ch = new MomentumCharacter_s();
    ch->character = loadFullCharacter(std::string(path));
    ch->buildCaches();
    return ch;
  } catch (...) {
    return nullptr;
  }
}

void mb_character_destroy(MomentumCharacter ch) {
  delete ch;
}

int32_t mb_character_num_joints(MomentumCharacter ch) {
  if (!ch) return 0;
  return static_cast<int32_t>(ch->character.skeleton.joints.size());
}

int32_t mb_character_num_model_params(MomentumCharacter ch) {
  if (!ch) return 0;
  return static_cast<int32_t>(ch->character.parameterTransform.name.size());
}

const char* mb_character_joint_name(MomentumCharacter ch, int32_t jointIndex) {
  if (!ch || jointIndex < 0 ||
      jointIndex >= static_cast<int32_t>(ch->jointNameCache.size())) {
    return nullptr;
  }
  return ch->jointNameCache[jointIndex].c_str();
}

int32_t mb_character_joint_parent(MomentumCharacter ch, int32_t jointIndex) {
  if (!ch || jointIndex < 0 ||
      jointIndex >= static_cast<int32_t>(ch->character.skeleton.joints.size())) {
    return -1;
  }
  const auto parent = ch->character.skeleton.joints[jointIndex].parent;
  if (parent == kInvalidIndex) {
    return -1;
  }
  return static_cast<int32_t>(parent);
}

int32_t mb_character_find_joint(MomentumCharacter ch, const char* name) {
  if (!ch || !name) return -1;
  const auto id = ch->character.skeleton.getJointIdByName(name);
  if (id == kInvalidIndex) return -1;
  return static_cast<int32_t>(id);
}

const char* mb_character_param_name(MomentumCharacter ch, int32_t paramIndex) {
  if (!ch || paramIndex < 0 ||
      paramIndex >= static_cast<int32_t>(ch->paramNameCache.size())) {
    return nullptr;
  }
  return ch->paramNameCache[paramIndex].c_str();
}

// ---------------------------------------------------------------------------
// Forward Kinematics
// ---------------------------------------------------------------------------

MomentumSkeletonState mb_fk_from_model_params(
    MomentumCharacter ch,
    const float* modelParams,
    int32_t numParams) {
  if (!ch || !modelParams) return nullptr;

  const auto& pt = ch->character.parameterTransform;
  const int32_t expectedParams =
      static_cast<int32_t>(pt.name.size());
  if (numParams != expectedParams) return nullptr;

  try {
    // Map model params → joint params via the parameter transform
    Eigen::VectorXf mp =
        Eigen::Map<const Eigen::VectorXf>(modelParams, numParams);
    ModelParametersT<float> modelP(mp);
    JointParametersT<float> jp = pt.apply(modelP);

    auto* s = new MomentumSkeletonState_s();
    s->numJoints =
        static_cast<int32_t>(ch->character.skeleton.joints.size());
    s->state =
        SkeletonState(jp, ch->character.skeleton, /*computeDeriv=*/false);
    return s;
  } catch (...) {
    return nullptr;
  }
}

MomentumSkeletonState mb_fk_from_joint_params(
    MomentumCharacter ch,
    const float* jointParams,
    int32_t numJointParams) {
  if (!ch || !jointParams) return nullptr;

  const int32_t expected =
      static_cast<int32_t>(ch->character.skeleton.joints.size()) * kParametersPerJoint;
  if (numJointParams != expected) return nullptr;

  try {
    JointParametersT<float> jp =
        Eigen::Map<const Eigen::VectorXf>(jointParams, numJointParams);

    auto* s = new MomentumSkeletonState_s();
    s->numJoints =
        static_cast<int32_t>(ch->character.skeleton.joints.size());
    s->state =
        SkeletonState(jp, ch->character.skeleton, /*computeDeriv=*/false);
    return s;
  } catch (...) {
    return nullptr;
  }
}

MomentumSkeletonState mb_fk_bind_pose(MomentumCharacter ch) {
  if (!ch) return nullptr;
  try {
    const auto numJoints = ch->character.skeleton.joints.size();
    JointParametersT<float> jp =
        JointParametersT<float>::Zero(numJoints * kParametersPerJoint);
    // Set scale = 1.0 for each joint
    for (size_t i = 0; i < numJoints; ++i) {
      jp[i * kParametersPerJoint + 6] = 1.0f; // scale
    }

    auto* s = new MomentumSkeletonState_s();
    s->numJoints = static_cast<int32_t>(numJoints);
    s->state =
        SkeletonState(jp, ch->character.skeleton, /*computeDeriv=*/false);
    return s;
  } catch (...) {
    return nullptr;
  }
}

void mb_skeleton_state_destroy(MomentumSkeletonState state) {
  delete state;
}

MBTransform mb_skeleton_state_joint_transform(
    MomentumSkeletonState state,
    int32_t jointIndex) {
  MBTransform result = {{0, 0, 0, 1}, {0, 0, 0}, 1.0f};
  if (!state || jointIndex < 0 || jointIndex >= state->numJoints) {
    return result;
  }
  return toMBTransform(state->state.jointState[jointIndex].transform);
}

void mb_skeleton_state_all_transforms(
    MomentumSkeletonState state,
    MBTransform* outTransforms,
    int32_t maxJoints) {
  if (!state || !outTransforms) return;
  const int32_t count =
      (maxJoints < state->numJoints) ? maxJoints : state->numJoints;
  for (int32_t i = 0; i < count; ++i) {
    outTransforms[i] =
        toMBTransform(state->state.jointState[i].transform);
  }
}

MBVec3 mb_skeleton_state_joint_position(
    MomentumSkeletonState state,
    int32_t jointIndex) {
  MBVec3 result = {0, 0, 0};
  if (!state || jointIndex < 0 || jointIndex >= state->numJoints) {
    return result;
  }
  const auto& t = state->state.jointState[jointIndex].transform;
  return toMBVec3(t.translation);
}

// ---------------------------------------------------------------------------
// Character saving
// ---------------------------------------------------------------------------

bool mb_character_save(
    MomentumCharacter ch,
    const char* path,
    float fps,
    const float* motionData,
    int32_t numModelParams,
    int32_t numFrames) {
  if (!ch || !path) return false;
  try {
    Eigen::MatrixXf motion;
    if (motionData && numModelParams > 0 && numFrames > 0) {
      motion = Eigen::Map<const Eigen::MatrixXf>(
          motionData, numModelParams, numFrames);
    }
    saveCharacter(
        filesystem::path(path), ch->character, fps, motion);
    return true;
  } catch (...) {
    return false;
  }
}
