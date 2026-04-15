#!/usr/bin/env python3
"""
body_tracking_example.py — Momentum ボディトラッキング実行例

C3Dモーションキャプチャデータからキャラクターモデルのポーズを推定し、
アニメーションとして保存するパイプラインのデモンストレーション。

使い方:
  方法1: テストキャラクター + 合成マーカーデータ (依存ファイルなし)
    python body_tracking_example.py --mode synthetic

  方法2: C3Dファイル + キャラクターモデル (実データ)
    python body_tracking_example.py --mode c3d \
      --c3d path/to/markers.c3d \
      --model path/to/character.glb \
      --output tracked.glb

  方法3: 同梱テストデータ
    python body_tracking_example.py --mode test
"""

import argparse
import os
import sys
import tempfile
import time

import numpy as np


def run_synthetic_tracking():
    """テストキャラクター + 合成マーカーデータによるボディトラッキングデモ。
    外部ファイル不要。"""
    import pymomentum.geometry as pym_geometry
    import pymomentum.geometry_test_utils as pym_test_utils
    from pymomentum.marker_tracking import (
        calibrate_markers,
        CalibrationConfig,
        process_markers,
        refine_motion,
        RefineConfig,
        save_motion,
        TrackingConfig,
    )

    print("=" * 60)
    print("Body Tracking (合成マーカーデータ)")
    print("=" * 60)

    # ---------------------------------------------------------------
    # Step 1: テストキャラクター作成
    # ---------------------------------------------------------------
    print("\n[Step 1] テストキャラクター作成...")
    character = pym_test_utils.create_test_character()
    print(f"  ジョイント数    : {len(character.skeleton.joints)}")
    print(f"  パラメータ数    : {character.parameter_transform.size}")
    print(f"  ロケーター数    : {len(character.locators)}")
    print(f"  ジョイント名    : {[j.name for j in character.skeleton.joints]}")
    print(f"  ロケーター名    : {[loc.name for loc in character.locators]}")

    # ---------------------------------------------------------------
    # Step 2: 合成マーカーデータ生成
    # ---------------------------------------------------------------
    print("\n[Step 2] 合成マーカーデータ生成...")
    num_frames = 60
    marker_data = []
    for frame_i in range(num_frames):
        markers = []
        t = frame_i / num_frames
        for loc in character.locators:
            # ロケーターの初期位置 + 時間に応じた動き
            pos = np.array([0.0, 0.0, 0.0]) + np.array(loc.offset)
            # 簡単な正弦波動作を加える
            pos[0] += 5.0 * np.sin(2 * np.pi * t)  # X: 左右の揺れ
            pos[1] += 2.0 * np.sin(4 * np.pi * t)  # Y: 上下の揺れ
            marker = pym_geometry.Marker(loc.name, pos, False)
            markers.append(marker)
        marker_data.append(markers)
    print(f"  フレーム数      : {num_frames}")
    print(f"  マーカー数/フレーム: {len(marker_data[0])}")

    # ---------------------------------------------------------------
    # Step 3: キャリブレーション
    # ---------------------------------------------------------------
    print("\n[Step 3] キャリブレーション...")
    calib_config = CalibrationConfig(
        calib_frames=min(30, num_frames),
        major_iter=3,
        max_iter=30,
        loss_alpha=2.0,
        debug=False,
    )
    identity = np.zeros(0, dtype=np.float32)

    t0 = time.time()
    calibrated_identity = calibrate_markers(
        character, identity, marker_data, calib_config
    )
    t_calib = time.time() - t0
    print(f"  キャリブレーション完了: {t_calib:.2f}秒")
    print(f"  Identity パラメータ数: {calibrated_identity.shape[0]}")

    # ---------------------------------------------------------------
    # Step 4: フレームごとのトラッキング
    # ---------------------------------------------------------------
    print("\n[Step 4] ボディトラッキング...")
    tracking_config = TrackingConfig(
        max_iter=30,
        loss_alpha=2.0,
        smoothing=0.0,
        collision_error_weight=0.0,
        debug=False,
    )

    t0 = time.time()
    motion = process_markers(
        character,
        calibrated_identity,
        marker_data,
        tracking_config,
        calib_config,
        calibrate=False,  # 既にキャリブレーション済み
    )
    t_track = time.time() - t0
    print(f"  トラッキング完了: {t_track:.2f}秒")
    print(f"  モーション行列  : {motion.shape} (フレーム数 x パラメータ数)")

    # ---------------------------------------------------------------
    # Step 5: モーションリファインメント (オプション)
    # ---------------------------------------------------------------
    print("\n[Step 5] モーションリファインメント...")
    refine_config = RefineConfig(
        max_iter=20,
        smoothing=0.5,  # 時間的平滑化
        regularizer=0.1,
        debug=False,
    )

    t0 = time.time()
    refined_motion = refine_motion(
        character,
        calibrated_identity,
        motion,
        marker_data,
        refine_config,
    )
    t_refine = time.time() - t0
    print(f"  リファインメント完了: {t_refine:.2f}秒")
    print(f"  リファインド行列: {refined_motion.shape}")

    # ---------------------------------------------------------------
    # Step 6: 結果の保存
    # ---------------------------------------------------------------
    output_file = os.path.join(tempfile.gettempdir(), "body_tracking_result.glb")
    print(f"\n[Step 6] 結果保存: {output_file}")
    save_motion(
        output_file,
        character,
        calibrated_identity,
        refined_motion,
        marker_data,
        30.0,  # fps
        True,  # save marker mesh
    )
    print(f"  保存完了!")

    # ---------------------------------------------------------------
    # 結果サマリー
    # ---------------------------------------------------------------
    print("\n" + "=" * 60)
    print("結果サマリー")
    print("=" * 60)
    print(f"  総フレーム数           : {num_frames}")
    print(f"  キャリブレーション時間 : {t_calib:.2f}秒")
    print(f"  トラッキング時間       : {t_track:.2f}秒 ({num_frames / t_track:.1f} fps)")
    print(f"  リファインメント時間   : {t_refine:.2f}秒")
    print(f"  出力ファイル           : {output_file}")

    # モーションの統計
    print(f"\n  モーションパラメータ統計:")
    print(
        f"    mean  : {np.mean(np.abs(refined_motion)):.4f}"
    )
    print(
        f"    max   : {np.max(np.abs(refined_motion)):.4f}"
    )
    print(
        f"    std   : {np.std(refined_motion):.4f}"
    )
    return output_file


def run_c3d_tracking(c3d_path, model_path, output_path, params_path=None, locators_path=None):
    """実際のC3Dファイルとキャラクターモデルを使用したボディトラッキング。"""
    import pymomentum.geometry as pym_geometry
    from pymomentum.marker_tracking import (
        calibrate_markers,
        CalibrationConfig,
        process_markers,
        refine_motion,
        RefineConfig,
        save_motion,
        TrackingConfig,
    )

    print("=" * 60)
    print("Body Tracking (C3Dファイル)")
    print("=" * 60)

    # ---------------------------------------------------------------
    # Step 1: キャラクターモデル読み込み
    # ---------------------------------------------------------------
    print(f"\n[Step 1] キャラクターモデル読み込み: {model_path}")
    if params_path and locators_path:
        character = pym_geometry.Character.from_file(
            model_path, params_path, locators_path
        )
    else:
        character = pym_geometry.Character.from_file(model_path)
    print(f"  ジョイント数  : {len(character.skeleton.joints)}")
    print(f"  パラメータ数  : {character.parameter_transform.size}")
    print(f"  ロケーター数  : {len(character.locators)}")

    # ---------------------------------------------------------------
    # Step 2: C3Dマーカーデータ読み込み
    # ---------------------------------------------------------------
    print(f"\n[Step 2] C3Dマーカーデータ読み込み: {c3d_path}")
    sequences = pym_geometry.load_markers(c3d_path, main_subject_only=True)
    if not sequences:
        print("  エラー: マーカーデータが見つかりません")
        sys.exit(1)

    seq = sequences[0]
    marker_data = seq.frames
    fps = seq.fps
    print(f"  被験者名        : {seq.name}")
    print(f"  フレーム数      : {len(marker_data)}")
    print(f"  FPS             : {fps}")
    if marker_data:
        visible = [m for m in marker_data[0] if not m.occluded]
        print(f"  マーカー数 (総数): {len(marker_data[0])}")
        print(f"  マーカー数 (可視): {len(visible)}")
        print(f"  マーカー名 (先頭5): {[m.name for m in marker_data[0][:5]]}")

    # ---------------------------------------------------------------
    # Step 3: キャリブレーション
    # ---------------------------------------------------------------
    print("\n[Step 3] キャリブレーション...")
    calib_config = CalibrationConfig(
        calib_frames=100,
        major_iter=3,
        max_iter=30,
        loss_alpha=2.0,
        debug=True,
    )
    identity = np.zeros(0, dtype=np.float32)

    t0 = time.time()
    calibrated_identity = calibrate_markers(
        character, identity, marker_data, calib_config
    )
    t_calib = time.time() - t0
    print(f"  キャリブレーション完了: {t_calib:.2f}秒")

    # ---------------------------------------------------------------
    # Step 4: フレームごとのトラッキング
    # ---------------------------------------------------------------
    print("\n[Step 4] ボディトラッキング...")
    tracking_config = TrackingConfig(
        max_iter=30,
        loss_alpha=2.0,
        smoothing=0.1,  # 時間的平滑化
        collision_error_weight=0.0,
        debug=True,
    )

    t0 = time.time()
    motion = process_markers(
        character,
        calibrated_identity,
        marker_data,
        tracking_config,
        calib_config,
        calibrate=False,
    )
    t_track = time.time() - t0
    num_frames = len(marker_data)
    print(f"  トラッキング完了: {t_track:.2f}秒 ({num_frames / max(t_track, 0.001):.1f} fps)")
    print(f"  モーション行列  : {motion.shape}")

    # ---------------------------------------------------------------
    # Step 5: モーションリファインメント
    # ---------------------------------------------------------------
    print("\n[Step 5] モーションリファインメント...")
    refine_config = RefineConfig(
        max_iter=20,
        smoothing=1.0,
        regularizer=0.1,
        debug=True,
    )

    t0 = time.time()
    refined_motion = refine_motion(
        character,
        calibrated_identity,
        motion,
        marker_data,
        refine_config,
    )
    t_refine = time.time() - t0
    print(f"  リファインメント完了: {t_refine:.2f}秒")

    # ---------------------------------------------------------------
    # Step 6: 結果保存
    # ---------------------------------------------------------------
    print(f"\n[Step 6] 結果保存: {output_path}")
    save_motion(
        output_path,
        character,
        calibrated_identity,
        refined_motion,
        marker_data,
        fps,
        True,
    )
    print(f"  保存完了!")

    print("\n" + "=" * 60)
    print("結果サマリー")
    print("=" * 60)
    print(f"  入力            : {c3d_path}")
    print(f"  出力            : {output_path}")
    print(f"  フレーム数      : {num_frames}")
    print(f"  キャリブレーション: {t_calib:.2f}秒")
    print(f"  トラッキング    : {t_track:.2f}秒")
    print(f"  リファインメント: {t_refine:.2f}秒")
    return output_path


def run_test_data_tracking():
    """リポジトリ同梱のテストデータを使用。"""
    import pymomentum.geometry as pym_geometry
    from pymomentum.marker_tracking import (
        CalibrationConfig,
        process_markers,
        save_motion,
        TrackingConfig,
    )

    print("=" * 60)
    print("Body Tracking (同梱テストデータ)")
    print("=" * 60)

    # リポジトリのルートから相対パスでテストデータを探す
    repo_root = os.path.dirname(os.path.abspath(__file__))
    c3d_path = os.path.join(
        repo_root, "momentum", "examples", "process_markers_app", "02_01.c3d"
    )
    model_path = os.path.join(
        repo_root,
        "momentum",
        "examples",
        "convert_model",
        "test_data",
        "character.fbx",
    )
    locators_path = os.path.join(
        repo_root,
        "momentum",
        "examples",
        "convert_model",
        "test_data",
        "character.locators",
    )
    params_path = os.path.join(
        repo_root,
        "momentum",
        "examples",
        "convert_model",
        "test_data",
        "character.model",
    )

    # ファイル存在確認
    missing = []
    for path, label in [
        (c3d_path, "C3D data"),
        (model_path, "Character model"),
    ]:
        if not os.path.isfile(path):
            missing.append(f"  {label}: {path}")

    if missing:
        print("\n以下のファイルが見つかりません:")
        for m in missing:
            print(m)
        print(
            "\nヒント: モデルファイルがリポジトリに同梱されていない場合があります。"
        )
        print("--mode synthetic で合成データのデモを実行できます。")
        sys.exit(1)

    # C3Dデータを読み込む
    print(f"\n[Step 1] C3Dデータ読み込み: {c3d_path}")
    sequences = pym_geometry.load_markers(c3d_path, main_subject_only=True)
    if not sequences:
        print("  エラー: マーカーデータが見つかりません")
        sys.exit(1)

    seq = sequences[0]
    marker_data = seq.frames
    fps = seq.fps
    print(f"  フレーム数: {len(marker_data)}, FPS: {fps}")
    if marker_data:
        print(f"  マーカー数: {len(marker_data[0])}")
        print(f"  マーカー名: {[m.name for m in marker_data[0][:10]]}...")

    # キャラクターモデル読み込み
    print(f"\n[Step 2] キャラクターモデル読み込み: {model_path}")
    optional_args = {}
    if os.path.isfile(params_path):
        optional_args["params_path"] = params_path
    if os.path.isfile(locators_path):
        optional_args["locators_path"] = locators_path

    character = pym_geometry.Character.from_file(model_path)
    print(f"  ジョイント数: {len(character.skeleton.joints)}")
    print(f"  パラメータ数: {character.parameter_transform.size}")
    print(f"  ロケーター数: {len(character.locators)}")

    # トラッキング (キャリブレーション + トラッキング同時実行)
    print("\n[Step 3] キャリブレーション + トラッキング...")
    calib_config = CalibrationConfig(
        calib_frames=50,
        major_iter=3,
        max_iter=30,
        loss_alpha=2.0,
    )
    tracking_config = TrackingConfig(
        max_iter=30,
        loss_alpha=2.0,
        smoothing=0.1,
    )
    identity = np.zeros(0, dtype=np.float32)

    t0 = time.time()
    motion = process_markers(
        character,
        identity,
        marker_data,
        tracking_config,
        calib_config,
        calibrate=True,
        max_frames=100,  # デモなので最初の100フレームのみ
    )
    elapsed = time.time() - t0
    print(f"  完了: {elapsed:.2f}秒, モーション: {motion.shape}")

    # 保存
    output_path = os.path.join(tempfile.gettempdir(), "test_tracking_result.glb")
    print(f"\n[Step 4] 結果保存: {output_path}")
    save_motion(
        output_path,
        character,
        identity,
        motion,
        marker_data[:motion.shape[0]],
        fps,
        True,
    )
    print("  完了!")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Momentum Body Tracking パイプライン",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 合成データ (外部ファイル不要)
  python body_tracking_example.py --mode synthetic

  # 同梱テストデータ
  python body_tracking_example.py --mode test

  # C3Dファイルを指定
  python body_tracking_example.py --mode c3d \\
    --c3d markers.c3d \\
    --model character.glb \\
    --output tracked.glb
""",
    )
    parser.add_argument(
        "--mode",
        choices=["synthetic", "c3d", "test"],
        default="synthetic",
        help="トラッキングモード (default: synthetic)",
    )
    parser.add_argument("--c3d", help="C3D マーカーデータファイル")
    parser.add_argument("--model", help="キャラクターモデルファイル (.glb/.fbx)")
    parser.add_argument("--params", help="パラメータ変換ファイル (.model)")
    parser.add_argument("--locators", help="ロケーターファイル (.locators)")
    parser.add_argument("--output", default="tracked_output.glb", help="出力ファイル")
    args = parser.parse_args()

    if args.mode == "synthetic":
        run_synthetic_tracking()
    elif args.mode == "c3d":
        if not args.c3d or not args.model:
            parser.error("--mode c3d には --c3d と --model が必要です")
        run_c3d_tracking(
            args.c3d, args.model, args.output, args.params, args.locators
        )
    elif args.mode == "test":
        run_test_data_tracking()


if __name__ == "__main__":
    main()
