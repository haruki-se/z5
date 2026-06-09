# 金太郎飴 お絵かきボード

グリッド上に色を塗り、3Dプリンター（OctoPrint）で金太郎飴を自動製造するためのデスクトップアプリです。

## 必要環境

- Python 3.11 以上
- OctoPrint が稼働しているプリンター（同一ネットワーク上）

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install python-dotenv requests
```

### 2. APIキーの設定

`drawing_app/.env` ファイルを作成し、OctoPrint の API キーを記述します。

```
OCTOPRINT_API_KEY = "your_api_key_here"
```

APIキーは OctoPrint の **設定 → アプリケーションキー** から取得できます。

### 3. アプリの起動

```bash
cd drawing_app
python main.py
```

## 使い方

### デザインを描く

1. 上部の入力欄でグリッドのマス目数を指定し「適用」を押す（3〜16マス）
2. 下部のカラーボタン（白 / ピンク / 黄色）で色を選ぶ
3. グリッドをクリックまたはドラッグして色を塗る

### 複数デザインを配置する

- 「次のデザイン →」「← 前のデザイン」ボタンで描画対象のデザインを切り替える
- デザイン数の上限はプレートサイズから自動計算される
- 「前のデザインをコピー」で直前のデザインを複製できる

### ルートの確認

「ルートの可視化」ボタンを押すと、ノズルが各セルを巡る順序が赤い矢印で表示される。

### プリント

| ボタン | 動作 |
|---|---|
| G-code生成 | `output_plate.gcode` を生成するだけ（送信しない） |
| 生成してプリント | G-code を生成し、OctoPrint にアップロードしてプリントを開始する |

## 設定値の変更

[drawing_app/config.py](drawing_app/config.py) を編集します。

| 定数 | 説明 | デフォルト |
|---|---|---|
| `MAX_PRINTER_SIZE_X` | プレートの X 方向最大サイズ (mm) | 220.0 |
| `MAX_PRINTER_SIZE_Y` | プレートの Y 方向最大サイズ (mm) | 215.0 |
| `GLOBAL_Y_OFFSET` | ノズル取り付け位置による Y オフセット (mm) | 40.0 |
| `MATERIAL_SIZE` | 飴1個の一辺サイズ (mm) | 5.0 |
| `JOINT_SIZE` | ブロック間の目地幅 (mm) | 3.0 |
| `DESIGN_GAP` | デザイン同士の間隔 (mm) | 20.0 |
| `DRAW_Z` | 素材に当たる Z 高さ (mm) | 2.0 |
| `SAFE_Z` | 移動時の退避 Z 高さ (mm) | 10.0 |
| `OCTOPRINT_URL` | OctoPrint の URL | `http://3dz5.local` |

## ファイル構成

```
drawing_app/
├── main.py          # エントリーポイント
├── app.py           # UIとイベント処理
├── gcode.py         # Gコード生成ロジック
├── octoprint.py     # OctoPrint API連携
├── config.py        # 定数・設定値
└── .env             # APIキー（gitには含まれない）
```
