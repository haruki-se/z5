import os
import sys
import subprocess
import tempfile
import socket
from pathlib import Path

_venv = Path(__file__).parent / ".venv"
_venv_python = _venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
_packages = ["flask", "python-dotenv", "requests", "qrcode", "pillow"]

if sys.prefix == sys.base_prefix:
    # 仮想環境の外から起動された場合：venvを作ってそちらで再起動する
    if not _venv.exists():
        print("初回セットアップ: 仮想環境を作成中...")
        subprocess.run([sys.executable, "-m", "venv", str(_venv)], check=True)
    print("パッケージをインストール中...")
    subprocess.run([str(_venv_python), "-m", "pip", "install", "--quiet"] + _packages)
    result = subprocess.run([str(_venv_python)] + sys.argv)
    sys.exit(result.returncode)

sys.path.insert(0, str(Path(__file__).parent.parent / "drawing_app"))

from flask import Flask, request, jsonify, render_template
import gcode as gc
import octoprint
import config

app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config")
def get_config():
    return jsonify({
        "colors":          config.COLORS,
        "gridSizeMin":     config.GRID_SIZE_MIN,
        "gridSizeMax":     config.GRID_SIZE_MAX,
        "gridSizeDefault": config.GRID_SIZE_DEFAULT,
    })


@app.route("/api/gcode", methods=["POST"])
def generate_gcode():
    data = request.get_json()
    pages = [
        {color: [tuple(cell) for cell in cells] for color, cells in page.items()}
        for page in data["pages"]
    ]
    content = gc.build_gcode(pages, data["gridSize"])
    return content, 200, {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": "attachment; filename=output_plate.gcode",
    }


@app.route("/api/print", methods=["POST"])
def print_gcode():
    data = request.get_json()
    pages = [
        {color: [tuple(cell) for cell in cells] for color, cells in page.items()}
        for page in data["pages"]
    ]
    tmp = Path(tempfile.gettempdir()) / "output_plate.gcode"
    gc.save_gcode(pages, data["gridSize"], str(tmp))
    try:
        ref = octoprint.upload_and_print(str(tmp))
        return jsonify({"ok": True, "ref": ref})
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _get_lan_ip():
    # Debian系OS(Raspberry Pi OS含む)は /etc/hosts に "127.0.1.1 <hostname>" を
    # 持つことが多く、gethostbyname(gethostname()) だとループバックが返ってしまう。
    # 実際に送信はしないUDP接続でデフォルトルートのIPを引く方式にする。
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    port = config.WEB_PORT
    local_ip = _get_lan_ip()

    url = f"http://{local_ip}:{port}"
    print(f"\n  PC:          http://localhost:{port}")
    print(f"  smartphone:  {url}")

    env_path = Path(__file__).parent.parent / "drawing_app" / ".env"
    if env_path.exists():
        print(f"  .env:        {env_path} [OK]")
    else:
        print(f"  .env:        {env_path} [NOT FOUND]")
        print(f"               .env.sample を参考に上記パスに .env を作成してください")
    print()

    try:
        import qrcode, io
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)

        buf = io.StringIO()
        qr.print_ascii(out=buf, invert=True)
        sys.stdout.buffer.write(buf.getvalue().encode("utf-8"))
        sys.stdout.buffer.flush()
        print()

        qr_path = Path(__file__).parent / "qr_code.png"
        qr.make_image(fill_color="black", back_color="white").save(qr_path)
        print(f"  QR画像:      {qr_path}\n")
    except Exception:
        pass

    app.run(host="0.0.0.0", port=port, debug=False)
