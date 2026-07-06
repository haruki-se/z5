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
├── Raspberry_Pi/
│   ├── sol3.py                   # ソレノイド制御スクリプト（Raspberry Pi用）
│   └── kintaro-web.service       # web_appをPi起動時に自動起動させるsystemdユニット
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

以下のどちらかで起動してください。

| 方法 | 手順 |
|---|---|
| エクスプローラーから | `金太郎飴code_exe/start_web.bat` をダブルクリック |
| VS Code から | `金太郎飴code_exe/web_app.py` を開いて ▶ ボタンをクリック |

- **初回のみ:** 仮想環境（`.venv/`）の作成と必要パッケージのインストールが自動で行われます（数分かかる場合があります）
- **2回目以降:** 即座に起動します

起動すると以下のようなURLとQRコードが表示されます。

```
  PC:          http://localhost:5000
  smartphone:  http://192.168.x.x:5000
```

スマートフォンのカメラでQRコードを読み取るか、`smartphone:` のURLをブラウザで開いてください。

### 使い方

**デザインを描く（積み重ね方式・金太郎飴）**

このアプリは飴を1段ずつ積み重ねて金太郎飴を作ります。全レイヤーで断面（マス目数）は共通です。

1. 画面上部のドロップダウンでグリッドのマス目数を選ぶ（3〜16マス）
   - マス目数を選べるのは最初の1レイヤー目だけ。2レイヤー目を追加すると、以降は変更できなくなる
2. カラーボタン（白 / ピンク / 黄色）で色を選ぶ
3. グリッドをタップまたはドラッグして色を塗る
4. 消しゴムボタンで塗った色を消せる

**レイヤーを積み重ねる**

- 「レイヤー追加」で新しい段（レイヤー）を追加する（段数の上限なし。1段 = 素材1個分の高さ = MATERIAL_SIZE mm）
- 「◀ ▶」ボタンで編集対象のレイヤーを切り替える
- 「前レイヤーをコピー」で直前のレイヤーを複製できる
- 「リセット」で現在のレイヤーを白紙に戻す
- プリント時は全レイヤーが隙間なく塗られている必要がある（未塗装のマスがあるとエラーになる）
- プリントが完了すると、また最初にマス目数を設定するところからやり直しになる

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
| `GLOBAL_Y_OFFSET` | ノズル取り付け位置による Y オフセット (mm) | 26.0 |
| `CENTER_X` / `CENTER_Y` | 実機でジョグして確認したプレート中央のノズル座標 (mm) | 106.70 / 149.00 |
| `MATERIAL_SIZE` | 飴 1 個の一辺サイズ (mm)。積み重ね時の1段分の高さでもある | 5.0 |
| `JOINT_SIZE` | ブロック間の目地幅 (mm) | 2.5 |
| `DRAW_Z` | 最下段(1層目)で素材に当たる Z 高さ (mm) | -1.0 |
| `SAFE_Z_LAYER1` | 1層目の DRAW_Z に加える退避の余白 (mm) | 7.0 |
| `SAFE_Z_LAYER2_PLUS` | 2層目以降の DRAW_Z に加える退避の余白 (mm) | 7.0 |
| `END_X` / `END_Y` / `END_Z` | 印刷終了後にノズルを移動させる位置 (mm) | -13.0 / 227.0 / 50.0 |
| `OCTOPRINT_URL` | OctoPrint の URL（`.env` の `OCTOPRINT_URL` で上書き可） | `http://3dz5.local` |
| `WEB_PORT` | Flaskサーバーのポート（`.env` の `WEB_PORT` で上書き可） | `5000` |

---

## 2. ソレノイド制御（`Raspberry_Pi/sol3.py`）

Raspberry Pi の GPIO ピンに接続したソレノイドを on / off / pulse で操作するスクリプトです。

### 必要環境

- Raspberry Pi（RPi.GPIO が使える環境）
- Python 3

### GPIO ピンの設定

[Raspberry_Pi/sol3.py](Raspberry_Pi/sol3.py) の先頭で変更します。

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

---

## 3. Raspberry Pi 単体運用（自動起動）

PCを使わず、Raspberry Pi単体（OctoPrint・ソレノイド制御と同居）でお絵かきWebアプリを常時起動しておく方法です。

### 構成

同一のRaspberry Pi（ホスト名例: `3dz5`）上で3つが同居します。

| サービス | ポート |
|---|---|
| OctoPrint（haproxy経由） | 80 |
| OctoPrint（内部） | 5000 |
| お絵かきWebアプリ（`web_app.py`） | **8080**（`.env` の `WEB_PORT` で指定。OctoPrintと競合するため5000は使えない） |

ソレノイド制御（`sol3.py`）はOctoPrintの「GCODE System Commands」プラグイン経由で呼び出される仕組みのため、このデプロイでは変更不要です。

### OctoPrintのセットアップ（未インストールの場合）

SDカードを作り直した等でOctoPrintが入っていない状態から始める場合の手順。**このPiはRAMが415MB程度と非常に少なく、`/tmp` がRAMディスク(tmpfs, 200MB程度)になっているため、素の`pip install`だと`No space left on device`で失敗する**。必ずTMPDIRをディスク上のディレクトリに向けること。

1. venvを作成してインストール:
   ```bash
   python3 -m venv ~/oprint
   mkdir -p ~/pip-tmp
   source ~/oprint/bin/activate
   TMPDIR=~/pip-tmp pip install --upgrade pip
   TMPDIR=~/pip-tmp pip install octoprint
   deactivate
   ```
   （Python 3.13でも動作確認済み。TMPDIRを指定しないと依存パッケージのビルド中にtmpfsが埋まって失敗する）
2. シリアルポート（プリンタ）にアクセスできるようグループ追加:
   ```bash
   sudo usermod -aG dialout,tty z5
   ```
3. systemdサービスを作成（ポート5000で起動）:
   ```bash
   sudo tee /etc/systemd/system/octoprint.service <<'EOF'
   [Unit]
   Description=OctoPrint
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=z5
   ExecStart=/home/z5/oprint/bin/octoprint serve --host=0.0.0.0 --port=5000
   Restart=on-failure
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   EOF
   sudo systemctl daemon-reload
   sudo systemctl enable --now octoprint
   ```
4. haproxyをインストールし、ポート80→5000に転送する設定を追記:
   ```bash
   sudo apt-get update
   sudo apt-get install -y haproxy
   sudo tee -a /etc/haproxy/haproxy.cfg <<'EOF'

   frontend octoprint_frontend
       bind *:80
       default_backend octoprint_backend

   backend octoprint_backend
       timeout connect 10s
       timeout server 3600s
       server octoprint1 127.0.0.1:5000
   EOF
   sudo haproxy -c -f /etc/haproxy/haproxy.cfg   # 設定チェック
   sudo systemctl restart haproxy
   sudo systemctl enable haproxy
   ```
5. ブラウザで `http://3dz5.local` を開き、初回セットアップウィザードを完了する（管理者アカウント作成、プリンタ接続設定はプリンタ未接続なら後回しでよい）。
6. Settings → Application Keys で新しいキーを発行し、`drawing_app/.env` の `OCTOPRINT_API_KEY` に設定する（プレースホルダーのまま残すとHTTPヘッダーに使えない文字でクラッシュするので要注意）。

### デプロイ手順

1. PiにSSH接続する: `ssh z5@3dz5.local`
2. リポジトリをclone（2回目以降は `git pull`）:
   ```bash
   git clone -b test https://github.com/haruki-se/z5.git ~/kintaro-app
   ```
   （`test` ブランチで検証中のため明示的に指定。`main`/`master` に統合され次第、指定不要になる予定）
   リポジトリがprivateの場合は、事前にPi側でGitHubの認証情報（PATなど）を設定してください。
   `git pull` で更新した後は、実行中のサーバーに反映するため `sudo systemctl restart kintaro-web` も忘れずに実行してください。
3. `drawing_app/.env` を作成し、以下を設定する:
   ```
   OCTOPRINT_API_KEY=（OctoPrintのアプリケーションキー）
   WEB_PORT=8080
   OCTOPRINT_URL=http://localhost
   ```
4. 初回のみ手動起動して仮想環境を作らせる（起動ログでURL・QRが出ることを確認したら Ctrl+C）:
   ```bash
   cd ~/kintaro-app/金太郎飴code_exe
   python3 web_app.py
   ```
5. systemdサービスを登録し、自動起動を有効化する:
   ```bash
   sudo cp ~/kintaro-app/Raspberry_Pi/kintaro-web.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now kintaro-web
   ```
6. 動作確認:
   ```bash
   systemctl status kintaro-web
   journalctl -u kintaro-web -n 40   # 起動時のURL・ASCII QRを確認
   ```
   スマホでQR画像を見たい場合は、生成された `qr_code.png` を取得します:
   ```bash
   scp z5@3dz5.local:~/kintaro-app/金太郎飴code_exe/qr_code.png .
   ```
7. `sudo reboot` 後、`systemctl status kintaro-web` で自動起動を確認する。

### アクセスURL

- 推奨（固定・OctoPrintと同じmDNSホスト名）: `http://3dz5.local:8080`
- 起動ごとの実IPは `journalctl -u kintaro-web` や `qr_code.png` で確認: `http://<PiのLAN IP>:8080`

### 日常の操作

#### アクセスする

基本はスマホ・PCのブラウザで `http://3dz5.local:8080` を開くだけでよい。IPアドレスが変わっても影響を受けない。

QRコードで読み取りたい場合や、実際のIPアドレスを確認したい場合:
```bash
journalctl -u kintaro-web -n 40   # 起動時のURL・ASCII QRが見られる
```
画像として手元のPCに持ってきたい場合:
```bash
scp z5@3dz5.local:~/kintaro-app/金太郎飴code_exe/qr_code.png .
```
QRコード・表示される実IPは起動のたびに再生成され、Piのネットワーク環境（DHCP割り当て）が変わると内容も変わる。固定でアクセスしたい場合は上記の `3dz5.local` のURLを使うのが安全。

#### アプリを更新する（コード変更を取り込む）

```bash
cd ~/kintaro-app
git pull
sudo systemctl restart kintaro-web
```
`git pull` だけでは実行中のプロセスには反映されないため、`systemctl restart` を忘れずに実行する。

#### サービスの状態確認・起動/停止

```bash
systemctl status kintaro-web        # 状態確認
sudo systemctl restart kintaro-web  # 再起動（更新反映・不調時など）
sudo systemctl stop kintaro-web     # 停止
journalctl -u kintaro-web -f        # ログをリアルタイムで確認（Ctrl+Cで終了）
```

#### Wi-Fiが変わった場合

新しい場所で別のWi-Fiに接続したい場合は、次項「Wi-Fiネットワークの追加登録」を参照。

### Wi-Fiネットワークの追加登録

このPiのWi-Fi設定はNetworkManager（`nmcli`）で管理されている（`/etc/netplan/*.yaml` はNetworkManagerが自動生成した読み取り専用のエクスポートで、直接編集するものではない）。

複数の場所（Wi-Fi）で使う予定がある場合、あらかじめ空のプロファイルを登録しておき、後からSSID・パスワードを書き換えるだけで使えるようにできる。

**① 雛形を作成（今すぐ登録・今の接続には影響しない）**
```bash
sudo nmcli connection add type wifi con-name "wifi-template" ifname wlan0 ssid "CHANGE_ME" -- wifi-sec.key-mgmt wpa-psk wifi-sec.psk "CHANGE_ME" connection.autoconnect no
```

**② 実際に使うSSIDが決まったら書き換え**
```bash
sudo nmcli connection modify wifi-template wifi.ssid "実際のSSID" wifi-sec.psk "実際のパスワード" connection.autoconnect yes
```

**③ （任意）その場で接続確認**
```bash
sudo nmcli connection up wifi-template
nmcli -f GENERAL.STATE,IP4.ADDRESS device show wlan0
```

登録済みの接続一覧は `nmcli connection show` で確認できる。`autoconnect yes` にしておけば、以後は該当SSIDの電波が届く場所で自動的に接続される（既存の `utsuroi` 接続とは独立しており、優先順位は自動的に決まる）。
