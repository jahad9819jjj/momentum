# Momentum ボディトラッキング セットアップ & 実行ガイド

## 概要

Momentumのボディトラッキングは、**光学式モーションキャプチャのマーカーデータ (C3D)** から **キャラクターモデルのスケルトンポーズ** を推定するパイプラインです。

```
C3D マーカーデータ  ──┐
                      ├─→ キャリブレーション → トラッキング → リファインメント → GLB/FBX 出力
キャラクターモデル  ──┘
```

### パイプラインの各ステージ

| ステージ | 内容 | 入力 | 出力 |
|---|---|---|---|
| **1. データ読み込み** | C3Dファイルからマーカー3D位置を読み込み | .c3d | MarkerSequence |
| **2. キャリブレーション** | スケルトンのスケール・マーカー取り付け位置を校正 | マーカー, キャラクター | 校正済みIdentity |
| **3. トラッキング** | フレームごとにポーズを最適化 (Gauss-Newton) | マーカー, 校正済みモデル | モーション行列 |
| **4. リファインメント** | 時間的平滑化・衝突回避を適用 | モーション, マーカー | 平滑化モーション |
| **5. 保存** | GLB/FBXアニメーションとして書き出し | モーション, キャラクター | .glb/.fbx |

---

## セットアップ手順

### 方法A: pixi を使う（推奨）

```bash
# 1. pixiをインストール (まだの場合)
curl -fsSL https://pixi.sh/install.sh | bash

# 2. リポジトリに移動
cd /home/jhirai/meta/momentum

# 3. C++ライブラリをビルド & インストール
pixi run build

# 4. Pythonバインディングをビルド
pixi run build_py

# 5. テスト実行 (確認)
pixi run test_py
```

### 方法B: conda で手動セットアップ

```bash
# 1. 環境作成
conda create -n momentum python=3.12
conda activate momentum

# 2. 依存ライブラリインストール
conda install -c conda-forge \
    cmake ninja gtest pybind11 \
    eigen ceres-solver dispenso drjit-cpp \
    fmt spdlog nlohmann_json cli11 \
    openfbx ezc3d fx-gltf ms-gsl re2 \
    scipy pytest pytorch

# 3. ビルド
cd /home/jhirai/meta/momentum
pip install . -v --no-build-isolation

# 4. テスト
pytest pymomentum/test/test_process_markers.py -v
```

### 方法C: pip (実験的)

```bash
pip install pymomentum-cpu    # CPU版
# または
pip install pymomentum-gpu    # GPU版 (CUDA)
```

> ⚠️ PyPI版は実験的です。安定した運用にはpixi/condaを推奨。

---

## 実行方法

### Python: 合成データデモ（外部ファイル不要）

```bash
# pixi環境内で実行
pixi run python body_tracking_example.py --mode synthetic
```

このモードでは:
- 3ジョイントのテストキャラクターを自動生成
- 正弦波ベースの合成マーカーデータを生成
- キャリブレーション → トラッキング → リファインメント を実行
- `/tmp/body_tracking_result.glb` に出力

### Python: 同梱C3Dテストデータ

```bash
pixi run python body_tracking_example.py --mode test
```

同梱の `02_01.c3d` と `character.fbx` を使用。

### Python: 独自C3Dデータ

```bash
pixi run python body_tracking_example.py --mode c3d \
  --c3d path/to/your_markers.c3d \
  --model path/to/character.glb \
  --params path/to/character.model \
  --locators path/to/character.locators \
  --output tracked_result.glb
```

### C++: process_markers_app

```bash
# ビルド
pixi run build

# コンフィグファイルを使って実行
pixi run process_markers -- -c momentum/examples/process_markers_app/process_markers_calib.config

# またはコマンドライン引数で直接指定
pixi run process_markers -- \
  --input 02_01.c3d \
  --output tracked.glb \
  --model character.glb \
  --parameters character.model \
  --locators optitrack_biomech57.locators \
  --calibrate true \
  --max-tracking-iter 30
```

### C++: refine_motion

```bash
pixi run refine_motion -- \
  --input tracked.glb \
  --output refined.glb \
  --smoothing 1.0 \
  --collision-error-weight 1.0
```

### C++: c3d_viewer（マーカー可視化）

```bash
pixi run c3d_viewer -- --input 02_01.c3d --plot
```

> Rerun Viewer (`rerun`) が別途起動している必要があります。

---

## Python API リファレンス

### マーカーデータの読み込み

```python
import pymomentum.geometry as pym_geometry

# C3Dファイルから読み込み (.c3d, .trc, .glb をサポート)
sequences = pym_geometry.load_markers("markers.c3d", main_subject_only=True)
seq = sequences[0]

marker_data = seq.frames     # List[List[Marker]]  各フレームのマーカーリスト
fps = seq.fps                # float  フレームレート
name = seq.name              # str    被験者名

# マーカーの構造
marker = marker_data[0][0]
marker.name       # str: マーカー名
marker.pos         # numpy array (3,): 3D位置 (cm)
marker.occluded    # bool: 遮蔽されているか
marker.confidence  # float: 信頼度 [0, 1]
```

### キャラクターモデルの読み込み

```python
# GLBまたはFBXから読み込み
character = pym_geometry.Character.from_file("character.glb")

# パラメータ・ロケーター付き
character = pym_geometry.Character.from_file(
    "character.fbx",
    "character.model",
    "character.locators"
)

# 情報
character.skeleton.joints          # ジョイントリスト
character.parameter_transform.size # パラメータ数
character.locators                 # マーカー取り付け点
```

### キャリブレーション

```python
from pymomentum.marker_tracking import calibrate_markers, CalibrationConfig

config = CalibrationConfig(
    calib_frames=100,    # キャリブレーションに使うフレーム数 (均等サンプリング)
    major_iter=3,        # キャリブレーション反復回数
    max_iter=30,         # ソルバー最大反復数
    loss_alpha=2.0,      # 損失関数パラメータ (2.0=L2, <2で外れ値ロバスト)
    global_scale_only=False,  # True: 全体スケールのみ, False: 個別骨長も
    locators_only=False, # True: マーカー位置のみ校正
    calib_shape=False,   # True: ブレンドシェイプも校正
)

identity = np.zeros(0, dtype=np.float32)
calibrated_identity = calibrate_markers(
    character, identity, marker_data, config
)
```

### トラッキング

```python
from pymomentum.marker_tracking import process_markers, TrackingConfig

config = TrackingConfig(
    max_iter=30,                # ソルバー最大反復数
    loss_alpha=2.0,             # 損失関数 (2.0=L2)
    smoothing=0.1,              # 時間的平滑化重み (0=なし)
    collision_error_weight=0.0, # 衝突制約重み (0=なし)
    min_vis_percent=0.0,        # 最小可視マーカー割合
)

motion = process_markers(
    character,
    calibrated_identity,
    marker_data,
    config,
    calib_config,            # CalibrationConfig (calibrate=Trueの時使用)
    calibrate=False,         # True: キャリブレーション+トラッキング
    first_frame=0,           # 開始フレーム
    max_frames=0,            # 最大フレーム数 (0=全フレーム)
)
# motion: numpy array (num_frames, num_model_params)
```

### リファインメント

```python
from pymomentum.marker_tracking import refine_motion, RefineConfig

config = RefineConfig(
    max_iter=20,
    smoothing=1.0,              # 平滑化重み (強め)
    collision_error_weight=1.0, # 衝突制約
    regularizer=0.1,            # 元モーションへの正則化
    calib_id=False,             # True: Identityも再キャリブレーション
    calib_locators=False,       # True: ロケーターも再キャリブレーション
)

refined_motion = refine_motion(
    character,
    calibrated_identity,
    motion,
    marker_data,
    config,
)
```

### 保存

```python
from pymomentum.marker_tracking import save_motion

save_motion(
    "output.glb",           # 出力パス (.glb, .fbx, .gltf)
    character,
    calibrated_identity,
    refined_motion,
    marker_data,
    fps=30.0,               # フレームレート
    save_marker_mesh=True,  # マーカーの可視メッシュも保存
)
```

---

## パラメータチューニングガイド

### 損失関数 (loss_alpha)

| 値 | 損失関数 | 用途 |
|---|---|---|
| 2.0 | L2 (二乗誤差) | ノイズが少ない高品質データ |
| 1.0 | Pseudo-Huber (L2-L1) | 中程度のノイズ |
| 0.0 | Cauchy | ノイズの多いデータ |
| < 0 | Welsch | 外れ値が非常に多いデータ |

**推奨**: まず `2.0` で試し、トラッキングが不安定ならば `1.0` に下げる。

### 平滑化 (smoothing)

| 値 | 効果 |
|---|---|
| 0.0 | 平滑化なし (各フレーム独立) |
| 0.01-0.1 | 軽い平滑化 |
| 0.5-1.0 | 中程度の平滑化 |
| 5.0+ | 強い平滑化 (大きな動きが鈍る) |

### ソルバー反復数 (max_iter)

| 値 | トレードオフ |
|---|---|
| 10 | 高速だが精度低 |
| 30 | バランス（デフォルト） |
| 100 | 高精度だが低速 |

---

## 入力データ形式

### C3Dファイル

C3Dは光学式モーションキャプチャの標準フォーマットです。

| 項目 | 詳細 |
|---|---|
| マーカー | 3D位置 (x, y, z) + occluded フラグ |
| フレームレート | 通常 60-240 Hz |
| 座標系 | Y-up / Z-up (自動変換あり) |
| サポートシステム | OptiTrack, Vicon, Qualisys など |

### キャラクターモデル

| 形式 | 読み込み | 書き出し |
|---|---|---|
| .glb / .gltf | ✅ | ✅ |
| .fbx | ✅ (OpenFBX) | ✅ (要FBX SDK) |

キャラクターモデルには以下が必要:
- **スケルトン**: ジョイント階層構造
- **ロケーター**: マーカー取り付け位置（関連するジョイントとオフセット）
- **パラメータ変換**: モデルパラメータ→ジョイントパラメータのマッピング

---

## トラブルシューティング

### `ModuleNotFoundError: No module named 'pymomentum'`

```bash
# pixiでビルドしていない場合
pixi run build_py

# またはpipでインストール
pip install . -v --no-build-isolation
```

### `No markers found in C3D file`

- C3Dファイルが正しい形式か確認（ezc3dで読み込めるか）
- マーカー名がキャラクターのロケーター名と一致しているか確認

### トラッキング精度が低い

1. `loss_alpha` を `1.0` に下げる（ロバスト化）
2. `max_iter` を増やす（50-100）
3. `calib_frames` を増やす（200+）
4. マーカーのoccluded率が高い場合、`GapFillConfig` を有効化

### メモリ不足

- `max_frames` で処理フレーム数を制限
- 長いシーケンスはチャンクに分割して処理
