# Momentum リポジトリ解析

## 目的

Momentumは、**Meta（Facebook Research）** が開発したオープンソースライブラリで、**人体のキネマティックモーション（運動学的動作）** の基盤アルゴリズムと **数値最適化ソルバー** を提供することを目的としている。人体動作をさまざまなアプリケーションに適用するための基盤ライブラリとして設計されている。

主なユースケース:
- **順運動学・逆運動学（FK/IK）** による体のポーズ推定
- **モーションキャプチャデータの処理**（マーカーベースのトラッキング）
- **RGB/RGBDカメラからのボディトラッキング**
- **キャラクターアニメーション**（スケルトン、スキニング、ブレンドシェイプ）

## 機能

### コアモジュール（C++）

#### 1. Character（キャラクターモデリング）
- **Skeleton**: 階層的なジョイント構造の定義・管理
- **Parameter Transform**: モデルパラメータからジョイントパラメータへのマッピング（スパース行列による変換）
- **Parameter Limits**: パラメータの制約条件
- **Linear Skinning（LBS/SSD）**: 線形ブレンドスキニングによるメッシュ変形
- **Blend Shape**: PCAベースの形状変形（ベースシェイプ + ウェイト付きシェイプベクトル）
- **Pose Shape**: ポーズ依存のシェイプ補正
- **Collision Geometry**: 衝突ジオメトリ（SDF含む）

#### 2. Solver（数値最適化ソルバー）
- **Gauss-Newton Solver（密行列版）**: 非線形最小二乗問題のための反復解法。Levenberg-Marquardt正則化、バックトラッキング線探索をサポート
- **Sparse Gauss-Newton Solver（疎行列版）**: 大規模パラメータ空間向けの疎行列実装
- **Gradient Descent Solver**: 一次勾配降下法
- **Subset Gauss-Newton Solver**: パラメータのサブセットに対する最適化

#### 3. Character Solver（キャラクター特化ソルバー）
多数のエラー関数をサポート:
- **Position / Orientation / Projection Error Function**: 3D位置・方向・2D投影の誤差
- **Collision Error Function**: 衝突制約（SIMD最適化版あり）
- **Pose Prior Error Function**: ポーズ事前分布による制約
- **Floor / Height Error Function**: 床面・高さ制約
- **Aim / Normal / Plane Error Function**: 注視・法線・平面制約
- **Camera Projection Error Function**: カメラ投影誤差
- **Center of Mass Error Function**: 重心制約
- **SDF Collision Error Function**: Signed Distance Fieldベースの衝突判定
- **Vertex / Skinned Locator Error Function**: 頂点・スキンドロケーターの誤差
- **Trust Region QR**: QR分解ベースの信頼領域法

#### 4. Character Sequence Solver（シーケンスソルバー）
- **Sequence Solver**: フレームシーケンス全体に対する最適化
- **Multipose Solver**: 複数ポーズの同時最適化
- **Acceleration / Velocity / Jerk Sequence Error Function**: 加速度・速度・ジャークの時間的平滑化制約
- **Finite Difference Sequence Error Function**: 有限差分ベースの時間的制約

#### 5. Diff IK（微分可能逆運動学）
- **Fully Differentiable Body IK**: PyTorchの自動微分と統合し、IKソルバーの入力パラメータに対するロスの勾配を計算
- 各種微分可能エラー関数（距離、方向、位置、投影、ポーズ事前分布、スケルトン状態）

#### 6. Marker Tracking（マーカートラッキング）
- **Marker Tracker**: モーションキャプチャマーカーのトラッキング
- **Calibration**: ボディ・ロケーターのキャリブレーション（形状キャリブレーション含む）
- **Gap Fill**: マーカーの欠落データ補間
- **Generalized Loss**: ロバスト損失関数（L2、L1、Cauchy、Welschなど、α制御による外れ値耐性）

#### 7. I/O（入出力）
- **FBX**: OpenFBXによる読み込み（Autodesk FBX SDKによる書き出しはオプション）
- **glTF/GLB**: glTFフォーマットの読み書き（アニメーション、メッシュ、スケルトン）
- **BVH**: BVHモーションキャプチャフォーマット
- **C3D**: C3Dマーカーデータフォーマット（ezc3dライブラリ使用）
- **USD**: Universal Scene Descriptionフォーマット（オプション）
- **URDF**: ロボット記述フォーマット
- **Legacy JSON**: 独自JSONフォーマット

#### 8. Camera（カメラモデル）
- 複数のカメラ内部パラメータモデル（pinhole、OpenCV歪みモデル等）
- 3D→2D投影ユーティリティ
- drjitによるベクトル化された投影処理

#### 9. Rasterizer（ラスタライザー）
- ソフトウェアレンダリング（Phongシェーディング）
- テクスチャマッピングサポート
- mdspanベースのテンソルインターフェース

#### 10. Math（数学ライブラリ）
- **MPPCA**: Mixture of Probabilistic PCA（姿勢事前分布のモデリング）
- **Online Householder QR**: オンラインQR分解
- **Generalized Loss**: 適応型ロバスト損失関数
- **Transform**: 3D変換（回転、平行移動、スケール）
- **Mesh / Intersection**: メッシュ処理・交差判定

### Axelサブプロジェクト（空間データ構造）
- **BVH（Bounding Volume Hierarchy）**: バウンディングボリューム階層
- **BVH Embree**: Intel Embreeを使用した高速BVH
- **KdTree / SimdKdTree**: KD木（SIMD最適化版あり）
- **Signed Distance Field（SDF）**: 符号付き距離場（三線形補間）
- **Dual Contouring**: SDFからのメッシュ抽出
- **Mesh to SDF**: メッシュからSDFへの変換
- **TriBvh**: 三角形向けBVH（レイキャスト、最近傍点検索）

### Pythonバインディング（pymomentum）
- pybind11によるC++ APIのPythonラッパー
- **Tensor Momentum**: PyTorchテンソルとの統合（スケルトン状態、スキニング、ブレンドシェイプ等をGPU対応）
- **Tensor IK**: PyTorchベースの微分可能IKソルバー
- **Solver / Solver2**: Pythonからの最適化ソルバー利用
- **Renderer**: Pythonからのレンダリング機能
- NumPy/SciPyとの相互運用

### サンプルアプリケーション
- `hello_world`: 基本的な使い方
- `fbx_viewer`, `glb_viewer`, `bvh_viewer`, `c3d_viewer`, `urdf_viewer`, `usd_viewer`: 各フォーマットのビューワー（Rerun SDK使用）
- `convert_model`: モデル変換ツール
- `process_markers_app`: マーカー処理
- `refine_motion`: モーション改善
- `export_objs`: メッシュシーケンスのOBJエクスポート
- `animate_shapes`: ブレンドシェイプアニメーション

## 使用されている手法

### 数値最適化
- **Gauss-Newton法**: 非線形最小二乗問題の解法（ヤコビアン→ヘシアン近似）
- **Levenberg-Marquardt法**: 正則化付きGauss-Newton（数値安定性向上）
- **勾配降下法**: 一次最適化手法
- **Trust Region法**: QR分解ベースの信頼領域法
- **バックトラッキング線探索**: ステップサイズの適応的決定
- **Online Householder QR分解**: 逐次的QR分解

### キャラクターアニメーション
- **順運動学（Forward Kinematics）**: ジョイントパラメータから世界座標への変換
- **逆運動学（Inverse Kinematics）**: 目標位置からジョイントパラメータの逆算
- **Linear Blend Skinning（LBS）**: メッシュのスケルトンベース変形
- **PCAベースのBlend Shape**: 主成分分析による形状空間の表現
- **Pose Shape Correction**: ポーズに依存する形状補正

### 微分可能計算
- **Implicit Differentiation**: IKソルバーの解を通じた暗黙的微分（PyTorch自動微分との統合）
- **Tensor化されたFK/IK**: PyTorchテンソルによるバッチ処理・GPU計算

### 統計モデル
- **MPPCA（Mixture of Probabilistic PCA）**: ポーズ空間の確率的事前分布モデリング
- **Generalized Robust Loss**: 適応型ロバスト損失関数（α∈{-∞,...,0,1,2}で L2/L1/Cauchy/Welsch等を統一的に扱う）

### 空間データ構造・幾何計算
- **BVH（Bounding Volume Hierarchy）**: 衝突検出・空間クエリの高速化
- **KD木**: 最近傍探索
- **Signed Distance Field（SDF）**: 暗黙的表面表現と衝突判定
- **Dual Contouring**: SDFからのメッシュ再構成（シャープフィーチャ保持）
- **レイキャスティング**: 交差判定

### パフォーマンス最適化
- **SIMD命令**: 衝突判定・位置誤差計算等のベクトル化
- **drjit**: カメラ投影等のパケット化ベクトル演算
- **Intel Embree**: ハードウェア最適化されたBVH
- **Dispenso**: 並列実行フレームワーク
- **Tracy Profiler**: パフォーマンスプロファイリング

### 依存ライブラリ
- **Eigen**: 線形代数
- **Ceres Solver**: 非線形最小二乗（一部ユーティリティ）
- **PyTorch**: テンソル計算・自動微分（Pythonバインディング）
- **drjit**: ベクトル化演算
- **Rerun SDK**: データの可視化
- **OpenFBX**: FBXファイル読み込み
- **ezc3d**: C3Dファイル処理
- **fx-gltf**: glTFファイル処理
- **urdfdom**: URDFファイル処理
- **OpenUSD**: USDファイル処理（オプション）

## 制限

### ビルド・環境の制限
- **FBX書き出し**: Autodesk FBX SDKが別途必要（読み込みはOpenFBXで常時利用可能）
- **USD I/Oサポート**: オプション機能であり、デフォルトでは無効（`MOMENTUM_BUILD_IO_USD=OFF`）
- **Tracy Profiling**: Mac x86環境では非対応（CPUの不変TSC非対応のため）
- **PyPI対応**: 実験的（Experimental）。安定した利用にはConda/Pixiが推奨
- **CUDA/GPU**: PyTorchによるGPUサポートはPythonバインディングのみ。C++コアはCPUベース

### 機能的な制限
- **スキニング手法**: Linear Blend Skinning（LBS）のみ。Dual Quaternion Skinningなどは未実装
- **リアルタイムレンダリング**: ソフトウェアラスタライザーのみ（GPU対応レンダリングは非搭載）
- **drjit問題**: Linux/osx-arm64のScalar SIMDモードでdrjitがsegfaultする既知の問題あり（レンダリングテストがスキップされている）
- **テンプレート型**: C++ APIはfloat/doubleのテンプレート型をサポートしているが、一部コンポーネント（Skeleton等の構造体）はfloatのみ
- **ドキュメント**: C/C++ APIドキュメントはDoxygenベースだが、一部未完成の可能性あり

### プラットフォーム固有の制限
- **Windows**: Visual Studio 2022が必要。delvewheelによるDLLバンドリングが必要
- **Linux aarch64**: FBX SDK非対応（書き出し不可）。Tracy Profiler GUIなし。cibuildwheel非対応

## サポートしているOS

`pixi.toml`のplatforms設定に基づく:

| OS | アーキテクチャ | サポート状況 |
|---|---|---|
| **Linux** | x86_64 (linux-64) | ✅ フルサポート（CI、FBX SDK、Tracy GUI、cibuildwheel） |
| **Linux** | aarch64 (linux-aarch64) | ✅ サポート（一部制限あり：FBX書き出し不可、Tracy GUI/cibuildwheel非対応） |
| **macOS** | x86_64 (osx-64) | ✅ サポート（Tracy Profilingは非対応） |
| **macOS** | arm64 (osx-arm64) | ✅ フルサポート |
| **Windows** | x86_64 (win-64) | ✅ フルサポート（Visual Studio 2022使用） |

### Pythonバージョン
- Python 3.12
- Python 3.13

### ライセンス
- MIT License
