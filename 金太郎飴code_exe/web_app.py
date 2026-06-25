import sys
import tempfile
import socket
from pathlib import Path

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
        "maxPages":        gc.calc_layout(config.GRID_SIZE_MIN)["max_pages"],
    })


@app.route("/api/layout")
def get_layout():
    grid_size = int(request.args.get("gridSize", config.GRID_SIZE_DEFAULT))
    layout = gc.calc_layout(grid_size)
    return jsonify({"maxPages": layout["max_pages"]})


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


if __name__ == "__main__":
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"

    url = f"http://{local_ip}:5000"
    print(f"\n  PC:          http://localhost:5000")
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
    except Exception:
        pass

    app.run(host="0.0.0.0", port=5000, debug=False)
