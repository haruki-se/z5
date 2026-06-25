# 金太郎飴 お絵かきボード

グリッド上に色を塗り、3Dプリンター（OctoPrint）で金太郎飴を自動製造するためのWebアプリです。  
PCで起動したサーバーに、スマートフォン・タブレット・PCのブラウザからアクセスして使います。

## ファイル構成

```
金太郎飴code_ex/
├── 金太郎飴code_exe/             # Webアプリ本体
│   ├── start_web.bat             # ← ダブルクリックで起動
│   ├── web_app.py                # Flaskサーバー
│   ├── .venv/                    # 仮想環境（初回起動時に自動生成・gitには含まれない）
│   └── templates/
│       └── index.html            # ブラウザUI（スマホ対応）
├── drawing_app/                  # バックエンドロジック（web_appが内部で使用）
│   ├── gcode.py                  # G-code生成
│   ├── octoprint.py              # OctoPrint API連携
│   ├── config.py                 # 定数・設定値
│   ├── .env.sample               # .envの記述例
│   └── .env                      # APIキー（gitには含まれない・各自作成）
├── ラズパイに入れるプログラム/
│   └── sol3.py                   # ソレノイド制御スクリプト（Raspberry Pi用）
└── output_plate.gcode            # 生成されたG-code（自動上書き）
```

---

## 1. Webアプリ（メイン）

### 必要環境

- Python 3.11 以上（サーバー側PCのみ）
- スマートフォン・タブレットはブラウザのみでOK（Python不要）
- OctoPrint が稼働しているプリンター（同一ネットワーク上）
- スマートフォンとPCが**同じWi-Fi**に接続されていること

### セットアップ

**① `.env` ファイルの作成**

`drawing_app/.env.sample` をコピーして `drawing_app/.env` にリネームし、APIキーを記入します。

```
OCTOPRINT_API_KEY=your_api_key_here
```

> **注意:** `.env` は必ず `drawing_app/` フォルダの中に置いてください。  
> API キーは OctoPrint の **設定 → アプリケーションキー** から取得できます。  
> プリンターへの送信を使わずG-code生成のみの場合は `dummy` でも起動できます。

**② アプリの起動**

`金太郎飴code_exe/start_web.bat` をダブルクリックします。

- **初回のみ:** 仮想環境（`.venv/`）の作成と必要パッケージのインストールが自動で行われます（数分かかる場合があります）
- **2回目以降:** 即座に起動します

起動すると以下のようなURLとQRコードが表示されます。

```
  PC:          http://localhost:5000
  smartphone:  http://192.168.x.x:5000
```

スマートフォンのカメラでQRコードを読み取るか、`smartphone:` のURLをブラウザで開いてください。

### 使い方

**デザインを描く**

1. 画面上部のドロップダウンでグリッドのマス目数を選ぶ（3〜16マス）
2. カラーボタン（白 / ピンク / 黄色）で色を選ぶ
3. グリッドをタップまたはドラッグして色を塗る
4. 消しゴムボタンで塗った色を消せる

**複数デザインを配置する**

- 「◀ ▶」ボタンで描画対象のデザインを切り替える
- デザイン数の上限はプレートサイズから自動計算される
- 「前をコピー」で直前のデザインを複製できる
- 「リセット」で現在のデザインを白紙に戻す

**ルートの確認**

「ルート表示」ボタンを押すと、ノズルが各セルを巡る順序が赤い矢印で表示される。

**プリント**

| ボタン | 動作 |
|---|---|
| G-code ダウンロード | `output_plate.gcode` をブラウザからダウンロード |
| 生成してプリント | G-code を生成し、OctoPrint にアップロードしてプリントを開始する |

### 設定値の変更

[drawing_app/config.py](drawing_app/config.py) を編集します。

| 定数 | 説明 | デフォルト |
|---|---|---|
| `MAX_PRINTER_SIZE_X` | プレートの X 方向最大サイズ (mm) | 220.0 |
| `MAX_PRINTER_SIZE_Y` | プレートの Y 方向最大サイズ (mm) | 215.0 |
| `GLOBAL_Y_OFFSET` | ノズル取り付け位置による Y オフセット (mm) | 40.0 |
| `MATERIAL_SIZE` | 飴 1 個の一辺サイズ (mm) | 5.0 |
| `JOINT_SIZE` | ブロック間の目地幅 (mm) | 3.0 |
| `DESIGN_GAP` | デザイン同士の間隔 (mm) | 20.0 |
| `DRAW_Z` | 素材に当たる Z 高さ (mm) | 2.0 |
| `SAFE_Z` | 移動時の退避 Z 高さ (mm) | 10.0 |
| `OCTOPRINT_URL` | OctoPrint の URL | `http://3dz5.local` |

---

## 2. ソレノイド制御（`ラズパイに入れるプログラム/sol3.py`）

Raspberry Pi の GPIO ピンに接続したソレノイドを on / off / pulse で操作するスクリプトです。

### 必要環境

- Raspberry Pi（RPi.GPIO が使える環境）
- Python 3

### GPIO ピンの設定

[ラズパイに入れるプログラム/sol3.py](ラズパイに入れるプログラム/sol3.py) の先頭で変更します。

```python
PIN1 = 17   # ソレノイド 1
PIN2 = 22   # ソレノイド 2
PIN3 = 27   # ソレノイド 3

PULSE_TIME = 1.0  # パルス時間（秒）
```

### 使い方

```bash
python sol3.py [ソレノイド番号] [コマンド]
```

| 引数 | 値 | 説明 |
|---|---|---|
| ソレノイド番号 | `1` / `2` / `3` | 操作するソレノイドを選択 |
| コマンド | `on` | ピンを HIGH に保つ |
| | `off` | ピンを LOW にする |
| | `pulse` | `PULSE_TIME` 秒だけ HIGH にして戻す |

**例**

```bash
# ソレノイド 2 を 1 秒間パルス駆動
python sol3.py 2 pulse

# ソレノイド 1 を ON
python sol3.py 1 on

# ソレノイド 3 を OFF
python sol3.py 3 off
```
