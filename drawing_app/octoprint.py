import os
import config

try:
    import requests
    _requests_available = True
except ImportError:
    _requests_available = False


def _check_requests():
    if not _requests_available:
        raise RuntimeError(
            "'requests' ライブラリが見つかりません。\n"
            "ターミナルで  pip install requests  を実行してください。"
        )


def upload_and_print(file_path: str) -> str:
    """
    G-code ファイルを OctoPrint にアップロードし、即座に印刷を開始する。

    Args:
        file_path: アップロードする .gcode ファイルのパス

    Returns:
        OctoPrint から返された参照 URL 文字列

    Raises:
        RuntimeError: requests 未インストール、接続失敗、APIエラー時
    """
    _check_requests()

    url = f"{config.OCTOPRINT_URL.rstrip('/')}/api/files/local"
    headers = {"X-Api-Key": config.OCTOPRINT_API_KEY}
    filename = os.path.basename(file_path)

    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                headers=headers,
                files={"file": (filename, f, "application/octet-stream")},
                data={"print": "true", "select": "true"},
                timeout=30,
            )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"OctoPrint ({config.OCTOPRINT_URL}) に接続できません。\n"
            "URLとネットワーク接続を確認してください。"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("OctoPrint への接続がタイムアウトしました。")

    if response.status_code == 409:
        raise RuntimeError(
            "現在プリント中のためファイルを送信できません。\n"
            "プリントが終わってから再試行してください。"
        )
    if not response.ok:
        raise RuntimeError(
            f"OctoPrint API エラー: HTTP {response.status_code}\n{response.text}"
        )

    data = response.json()
    return data.get("refs", {}).get("resource", url)
