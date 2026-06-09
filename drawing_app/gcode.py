# gcode.py - Gコード生成ロジック
#
# プリンターへの動作指示（Gコード）を生成する関数群です。
# UI（tkinter）には一切依存していないため、単独でテストや再利用が可能です。
#
# 主な処理の流れ:
#   1. calc_layout()  : プレートサイズからデザインの配置数・開始座標を計算
#   2. generate_snake_route() : ノズルが無駄に移動しない蛇行順序を生成
#   3. build_gcode()  : 全デザインの色情報をもとに Gコード文字列を組み立て
#   4. save_gcode()   : build_gcode() の結果をファイルに書き出す

import os
import config


def generate_snake_route(grid_size: int) -> list[tuple[int, int]]:
    """
    蛇行（スネーク）順のセル座標リストを返す。

    偶数行は左→右、奇数行は右→左の順に並べることで、
    ノズルの無駄な長距離移動を減らす。

    Args:
        grid_size: グリッドの一辺のマス数

    Returns:
        (row, col) のタプルリスト
    """
    route = []
    for row in range(grid_size):
        # 偶数行: 左から右へ / 奇数行: 右から左へ（折り返し）
        cols = range(grid_size) if row % 2 == 0 else range(grid_size - 1, -1, -1)
        for col in cols:
            route.append((row, col))
    return route


def calc_layout(grid_size: int) -> dict:
    """
    プレートサイズとノズルオフセットをもとに、デザインの配置情報を計算する。

    X方向・Y方向それぞれについて何個のデザインを並べられるかを求め、
    プレート中央に寄せるための開始オフセットも計算する。

    Args:
        grid_size: グリッドの一辺のマス数

    Returns:
        以下のキーを持つ dict:
            n_cols (int)          : X方向に並べられるデザイン数
            n_rows (int)          : Y方向に並べられるデザイン数
            max_pages (int)       : 合計配置可能デザイン数 (n_cols × n_rows)
            start_offset_x (float): 中央寄せのための X 方向開始座標 (mm)
            start_offset_y (float): 中央寄せのための Y 方向開始座標 (mm)
            design_size (float)   : デザイン1個の物理サイズ (mm)
            avail_y (float)       : ノズルオフセット考慮後の Y 方向有効範囲 (mm)
    """
    # デザイン1個の物理サイズ（セルピッチ × マス数）
    design_size = config.CELL_SPACE * grid_size

    avail_x = config.MAX_PRINTER_SIZE_X
    # Y方向はノズルオフセット分だけ使える範囲が狭まる
    avail_y = config.MAX_PRINTER_SIZE_Y - config.GLOBAL_Y_OFFSET

    # 各方向に何個並べられるか（最低1個は保証）
    n_cols = max(1, int((avail_x + config.DESIGN_GAP) / (design_size + config.DESIGN_GAP)))
    n_rows = max(1, int((avail_y + config.DESIGN_GAP) / (design_size + config.DESIGN_GAP)))

    # 全デザインを並べたときの合計長さ
    total_len_x = n_cols * design_size + (n_cols - 1) * config.DESIGN_GAP
    total_len_y = n_rows * design_size + (n_rows - 1) * config.DESIGN_GAP

    # 中央寄せのための開始オフセット（余白を左右・上下に均等に配分）
    start_offset_x = (avail_x - total_len_x) / 2
    start_offset_y = (avail_y - total_len_y) / 2

    return {
        "n_cols":         n_cols,
        "n_rows":         n_rows,
        "max_pages":      n_cols * n_rows,
        "start_offset_x": start_offset_x,
        "start_offset_y": start_offset_y,
        "design_size":    design_size,
        "avail_y":        avail_y,
    }


def build_gcode(pages: list[dict], grid_size: int) -> str:
    """
    全ページのデザインデータから Gコード文字列を生成して返す。

    各デザインをスネークルート順にたどり、セルの色に応じた
    ノズルコマンド（OCTO90X）を出力する。
    白セルは「有色ブロックが1つでも存在するデザイン」にのみ出力される
    （全白の空デザインはスキップ）。

    Args:
        pages:     ページデータのリスト。
                   各要素は {"white": [(r,c), ...], "pink": [...], "yellow": [...]}
        grid_size: 現在のグリッドの一辺のマス数

    Returns:
        Gコード文字列
    """
    layout = calc_layout(grid_size)
    n_cols         = layout["n_cols"]
    n_rows         = layout["n_rows"]
    start_offset_x = layout["start_offset_x"]
    start_offset_y = layout["start_offset_y"]
    design_size    = layout["design_size"]

    route = generate_snake_route(grid_size)

    # --- ヘッダー部 ---
    gcode  = "; 平面配置自動レイアウトモード\n"
    gcode += f"; 素材ピッチ: {config.CELL_SPACE}mm (素材{config.MATERIAL_SIZE}mm + 目地{config.JOINT_SIZE}mm)\n"
    gcode += f"; 自作ノズルオフセット: Y+{config.GLOBAL_Y_OFFSET}mm, Y物理限界: {config.MAX_PRINTER_SIZE_Y}mm\n"
    # プリンター初期化: ヒーター停止 → ホーミング → 絶対座標モード → mm単位モード
    gcode += "M140 S0\nM104 S0\nG28\nG90\nG21\n"

    # --- デザインごとの出力 ---
    for page_index, page_data in enumerate(pages):
        # プレートに収まる最大数を超えたら打ち切り
        if page_index >= n_cols * n_rows:
            break

        # 全色のリストが空 = 未描画デザイン → スキップ
        is_empty = all(not page_data.get(color) for color in config.COLORS)
        if is_empty:
            continue

        # 有色ブロックが1つでもあれば白セルも出力する（背景として必要なため）
        has_colored_blocks = bool(page_data["pink"] or page_data["yellow"])

        # このデザインのプレート上の基準座標を計算
        col_idx = page_index % n_cols   # 何列目か
        row_idx = page_index // n_cols  # 何行目か
        page_origin_x = start_offset_x + col_idx * (design_size + config.DESIGN_GAP)
        page_origin_y = start_offset_y + row_idx * (design_size + config.DESIGN_GAP)

        gcode += f"\n; --- デザイン {page_index + 1} 開始 ---\n"
        gcode += f"G0 Z{config.SAFE_Z:.2f} F{config.F_SPEED}\n"  # まず安全高さへ退避

        # スネークルート順に各セルを処理
        for row, col in route:
            # セルの色を判定（pink → yellow → white の優先順位）
            color = None
            if (row, col) in page_data["pink"]:
                color = "pink"
            elif (row, col) in page_data["yellow"]:
                color = "yellow"
            elif (row, col) in page_data["white"] or has_colored_blocks:
                color = "white"

            if color:
                # セル中心のプリンター座標を計算
                # X: デザイン原点 + セル列オフセット + 素材の半径
                x_pos = page_origin_x + (col * config.CELL_SPACE) + (config.MATERIAL_SIZE / 2)
                # Y: 同上 + ノズルのグローバルオフセット
                y_pos = page_origin_y + (row * config.CELL_SPACE) + (config.MATERIAL_SIZE / 2) + config.GLOBAL_Y_OFFSET

                gcode += f"G0 X{x_pos:.2f} Y{y_pos:.2f} F{config.F_SPEED}\n"  # 座標へ高速移動
                gcode += f"G1 Z{config.DRAW_Z:.2f} F{config.F_SPEED}\n"        # ノズルを素材位置まで下降
                gcode += "G4 P1000\n"                                           # 1秒待機（素材安定）
                gcode += f"{config.CMD_MAP.get(color, 'OCTO900')} ; {color.upper()}\n"  # 色ノズル噴射
                gcode += "G4 P1000\n"                                           # 1秒待機（素材定着）
                gcode += f"G0 Z{config.SAFE_Z:.2f} F{config.F_SPEED}\n"        # ノズルを安全高さへ退避

        gcode += "OCTO900 ; IDLE\n"  # ノズルをアイドル状態に戻す

    # --- フッター部: 終了動作 ---
    gcode += "G0 Z50 F2250\n"   # ノズルを高く退避
    gcode += "G28 X0 Y0\n"      # X・Y をホームへ戻す
    gcode += "M84\n"             # モーターをオフ
    return gcode


def save_gcode(pages: list[dict], grid_size: int, file_path: str = "output_route.gcode") -> None:
    """
    Gコードを生成してファイルに保存する。

    Args:
        pages:     ページデータのリスト
        grid_size: 現在のグリッドサイズ
        file_path: 出力先ファイルパス（デフォルト: output_route.gcode）
    """
    content = build_gcode(pages, grid_size)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"平面配置G-codeを生成しました: {os.path.abspath(file_path)}")