# Momentum Swift ブリッジ — セットアップガイド

SwiftからMomentum C++ライブラリを使用するための手順です。

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────┐
│  Swift Application (main.swift)                 │
│    import Momentum                              │
├─────────────────────────────────────────────────┤
│  Swift Wrapper (Momentum.swift)                 │
│    class Character, class SkeletonState, ...    │
├─────────────────────────────────────────────────┤
│  C Module (CMomentum / module.modulemap)        │
│    MomentumBridge.h (C API)                     │
├─────────────────────────────────────────────────┤
│  C++ Implementation (MomentumBridge.cpp)        │
│    → libMomentumBridge.so / .dylib              │
├─────────────────────────────────────────────────┤
│  Momentum C++ Library                           │
│    libmomentum_character.so, etc.               │
└─────────────────────────────────────────────────┘
```

SwiftはC++を直接呼び出せない（テンプレート、Eigen、STL等）ため、以下の構成で橋渡しします:

1. **MomentumBridge.h** — `extern "C"` のフラットC API（opaqueハンドル + POD構造体）
2. **MomentumBridge.cpp** — C++で実装、Momentumライブラリを呼び出す
3. **module.modulemap** — SwiftのClangモジュールシステムへの登録
4. **Momentum.swift** — Swift側のラッパー（安全でSwift的なインターフェース）

## ファイル一覧

```
swift_bridge/
├── CMakeLists.txt              # Cブリッジライブラリのビルド
├── MomentumBridge.h            # C API ヘッダー
├── MomentumBridge.cpp          # C++ → C 実装
├── module.modulemap            # Swift用モジュールマップ
├── Package.swift               # Swift Package Manager 定義
├── Sources/
│   ├── Momentum/
│   │   └── Momentum.swift      # Swift ラッパーライブラリ
│   └── Example/
│       └── main.swift          # 使用例
└── README_SWIFT.md             # このファイル
```

## 前提条件

| ソフトウェア | バージョン | 備考 |
|---|---|---|
| Swift | 5.9+ | `swift --version` で確認 |
| CMake | 3.16+ | |
| Ninja | 任意 | |
| Pixi | 最新 | Momentumの依存管理 |
| OS | macOS or Linux | macOS推奨（Swiftツールチェーンが標準搭載） |

## 手順

### Step 1: Momentumライブラリをビルド・インストール

```bash
cd /path/to/momentum

# pixiを使った標準ビルド
pixi run config
pixi run build
pixi run install
```

これにより `$CONDA_PREFIX` にヘッダーとライブラリがインストールされます。

### Step 2: Cブリッジライブラリをビルド

```bash
cd swift_bridge

# Momentumのインストール先を指定してCMake構成
cmake -S . -B build \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=$CONDA_PREFIX \
  -DCMAKE_INSTALL_PREFIX=$CONDA_PREFIX

# ビルド
cmake --build build

# インストール (ヘッダーとライブラリを$CONDA_PREFIXへ)
cmake --build build --target install
```

ビルド成果物:
- `$CONDA_PREFIX/lib/libMomentumBridge.so` (Linux) / `.dylib` (macOS)
- `$CONDA_PREFIX/include/MomentumBridge.h`

### Step 3: Swiftからビルド・実行

#### 方法A: Swift Package Manager（推奨）

```bash
cd swift_bridge

# ライブラリパスをリンカに伝える
export LIBRARY_PATH=$CONDA_PREFIX/lib
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib  # Linux
export DYLD_LIBRARY_PATH=$CONDA_PREFIX/lib  # macOS

# C header の検索パスを設定
export C_INCLUDE_PATH=$CONDA_PREFIX/include

# ビルド
swift build \
  -Xlinker -L$CONDA_PREFIX/lib \
  -Xlinker -rpath -Xlinker $CONDA_PREFIX/lib \
  -Xcc -I$CONDA_PREFIX/include

# 実行
swift run Example
```

#### 方法B: swiftcで直接コンパイル

```bash
# 単一ファイルのコンパイル例
swiftc \
  -import-objc-header MomentumBridge.h \
  -L $CONDA_PREFIX/lib \
  -lMomentumBridge \
  -I . \
  -Xlinker -rpath -Xlinker $CONDA_PREFIX/lib \
  Sources/Example/main.swift \
  Sources/Momentum/Momentum.swift \
  -o momentum_example

./momentum_example
```

#### 方法C: Xcodeプロジェクト（macOS）

1. Xcodeで新規プロジェクト作成
2. **Build Settings**:
   - **Header Search Paths** に `$CONDA_PREFIX/include` を追加
   - **Library Search Paths** に `$CONDA_PREFIX/lib` を追加
   - **Other Linker Flags** に `-lMomentumBridge` を追加
   - **Runpath Search Paths** に `$CONDA_PREFIX/lib` を追加
3. **Bridging Header** に `MomentumBridge.h` のパスを設定
4. `Momentum.swift` をプロジェクトに追加
5. ビルド & 実行

## 使い方 (Swift)

```swift
import Momentum

// キャラクターモデル読み込み
guard let character = Character(path: "model.glb") else {
    fatalError("Failed to load model")
}
print("Joints: \(character.numJoints)")

// スケルトン階層の確認
for joint in character.joints {
    print("\(joint.name) (parent: \(joint.parentIndex ?? -1))")
}

// バインドポーズでFK計算
if let state = character.bindPose() {
    for i in 0..<character.numJoints {
        let pos = state.jointPosition(at: i)
        print("Joint \(i): (\(pos.x), \(pos.y), \(pos.z))")
    }
}

// モデルパラメータからFK計算
var params = [Float](repeating: 0, count: character.numModelParameters)
// params[index] = value  // パラメータを設定
if let state = character.forwardKinematics(modelParameters: params) {
    let transforms = state.allTransforms()
    // transforms[i].rotation, .translation, .scale
}
```

## 提供されるSwift API

### `Character` クラス
| プロパティ / メソッド | 説明 |
|---|---|
| `init?(path:)` | .glb/.fbx ファイルから読み込み |
| `numJoints` | ジョイント数 |
| `numModelParameters` | モデルパラメータ数 |
| `joints` | 全ジョイント情報の配列 |
| `findJoint(named:)` | 名前でジョイント検索 |
| `parameterNames` | 全パラメータ名 |
| `forwardKinematics(modelParameters:)` | モデルパラメータからFK |
| `forwardKinematics(jointParameters:)` | ジョイントパラメータからFK |
| `bindPose()` | バインドポーズでFK |
| `save(to:fps:)` | ファイルに保存 |

### `SkeletonState` クラス
| プロパティ / メソッド | 説明 |
|---|---|
| `numJoints` | ジョイント数 |
| `jointTransform(at:)` | 指定ジョイントのワールド変換 |
| `jointPosition(at:)` | 指定ジョイントのワールド位置 |
| `allTransforms()` | 全ジョイントの変換配列 |

## トラブルシューティング

### `dyld: Library not loaded: libMomentumBridge`
```bash
# LD_LIBRARY_PATH (Linux) or DYLD_LIBRARY_PATH (macOS) を設定
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

### `No such module 'CMomentum'`
module.modulemapが見つからない。`-I` フラグで swift_bridge ディレクトリを指定:
```bash
swift build -Xcc -I/path/to/swift_bridge
```

### Momentum自体のビルドエラー
Momentumの依存関係が揃っているか `pixi run config` の出力を確認してください。

### Linuxでの注意
- libstdc++ のバージョンがSwiftとMomentumで互換である必要があります
- pixi環境内で `swift build` を実行すると依存ライブラリが自動的に見える
