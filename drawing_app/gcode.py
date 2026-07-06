# gcode.py - Gコード生成ロジック
#
# プリンターへの動作指示（Gコード）を生成する関数群です。
# UI（tkinter）には一切依存していないため、単独でテストや再利用が可能です。
#
# 金太郎飴方式: 全レイヤーはX/Y座標（断面の形）が共通で、
# レイヤーごとにZ座標だけがMATERIAL_SIZE分ずつ積み上がっていきます。
#
# 主な処理の流れ:
#   1. calc_layout()  : プレート中央座標からデザインの開始座標を計算
#   2. generate_snake_route() : ノズルが無駄に移動しない蛇行順序を生成
#   3. build_gcode()  : 全レイヤーの色情報をもとに Gコード文字列を組み立て
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
    実測済みのプレート中央座標に合わせて、デザイン（断面）の開始座標を計算する。

    全レイヤーはこの同じX/Y座標を共有し、Z座標だけが積み重ねに応じて変わる。

    Args:
        grid_size: グリッドの一辺のマス数

    Returns:
        以下のキーを持つ dict:
            design_size (float)    : デザイン1個の物理サイズ (mm)
            start_offset_x (float) : デザイン原点(セル(0,0)側)の X 座標 (mm)
            start_offset_y (float) : デザイン原点(セル(0,0)側)の Y 座標 (mm)
    """
    # デザイン1個の物理サイズ（セルピッチ × マス数）
    design_size = config.CELL_SPACE * grid_size

    # 実測済みのプレート中央座標(config.CENTER_X/Y)にデザインの中心が来るよう配置する
    # Y側はセル座標計算時にGLOBAL_Y_OFFSETが別途加算されるため、ここで先に差し引いておく
    # +JOINT_SIZE/2 は design_size の末尾に含まれる余分な半目地ぶんの補正
    # （grid_sizeが奇数なら中央セル、偶数なら中央4セルの中点が、ちょうどCENTER_X/Yに一致する）
    start_offset_x = config.CENTER_X - design_size / 2 + config.JOINT_SIZE / 2
    start_offset_y = (config.CENTER_Y - config.GLOBAL_Y_OFFSET) - design_size / 2 + config.JOINT_SIZE / 2

    return {
        "design_size":    design_size,
        "start_offset_x": start_offset_x,
        "start_offset_y": start_offset_y,
    }


def build_gcode(pages: list[dict], grid_size: int) -> str:
    """
    全レイヤーの色情報から、飴を積み重ねるGコード文字列を組み立てる。

    pages[0] が最下段（1層目）で、以降のレイヤーは同じX/Y座標のまま
    MATERIAL_SIZE分ずつ高いZ座標に積み上がっていく（金太郎飴方式）。
    退避高さ(SAFE_Z_LAYER1 / SAFE_Z_LAYER2_PLUS)もタワーの高さに合わせて層ごとに底上げされる。

    Args:
        pages:     レイヤーデータのリスト（先頭が最下段）。
                   各要素は {"white": [(r,c), ...], "pink": [...], "yellow": [...]}
        grid_size: 全レイヤー共通のグリッドの一辺のマス数

    Returns:
        Gコード文字列
    """
    layout         = calc_layout(grid_size)
    start_offset_x = layout["start_offset_x"]
    start_offset_y = layout["start_offset_y"]

    route = generate_snake_route(grid_size)

    # --- ヘッダー部 ---
    gcode  = "; 積み重ねモード（金太郎飴方式）\n"
    gcode += f"; 素材ピッチ: {config.CELL_SPACE}mm (素材{config.MATERIAL_SIZE}mm + 目地{config.JOINT_SIZE}mm)\n"
    gcode += f"; 自作ノズルオフセット: Y+{config.GLOBAL_Y_OFFSET}mm, Y物理限界: {config.MAX_PRINTER_SIZE_Y}mm\n"
    # プリンター初期化: ヒーター停止 → ホーミング → 絶対座標モード → mm単位モード
    gcode += "M140 S0\nM104 S0\nG28\nG90\nG21\n"

    # --- レイヤーごとの出力（下から上へ積み上げる） ---
    for layer_index, page_data in enumerate(pages):
        # 有色ブロックが1つでもあれば白セルも出力する（背景として必要なため）
        has_colored_blocks = bool(page_data["pink"] or page_data["yellow"])

        # このレイヤーのZ高さ（1段ごとにMATERIAL_SIZE分だけ積み上がる）
        layer_draw_z = config.DRAW_Z + layer_index * config.MATERIAL_SIZE
        safe_z_margin = config.SAFE_Z_LAYER1 if layer_index == 0 else config.SAFE_Z_LAYER2_PLUS
        layer_safe_z = layer_draw_z + safe_z_margin

        gcode += f"\n; --- レイヤー {layer_index + 1} 開始 (Z={layer_draw_z:.2f}) ---\n"
        gcode += f"G0 Z{layer_safe_z:.2f} F{config.F_SPEED}\n"  # まず安全高さへ退避

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
                # セル中心のプリンター座標を計算（全レイヤー共通のX/Y）
                x_pos = start_offset_x + (col * config.CELL_SPACE) + (config.MATERIAL_SIZE / 2)
                y_pos = start_offset_y + (row * config.CELL_SPACE) + (config.MATERIAL_SIZE / 2) + config.GLOBAL_Y_OFFSET

                gcode += f"G0 X{x_pos:.2f} Y{y_pos:.2f} F{config.F_SPEED}\n"  # 座標へ高速移動
                gcode += f"G1 Z{layer_draw_z:.2f} F{config.F_SPEED}\n"        # ノズルを素材位置まで下降
                gcode += "G4 P1000\n"                                           # 1秒待機（素材安定）
                gcode += f"{config.CMD_MAP.get(color, 'OCTO900')} ; {color.upper()}\n"  # 色ノズル噴射
                gcode += "G4 P1000\n"                                           # 1秒待機（素材定着）
                gcode += f"G0 Z{layer_safe_z:.2f} F{config.F_SPEED}\n"        # ノズルを安全高さへ退避

        gcode += "OCTO900 ; IDLE\n"  # ノズルをアイドル状態に戻す

    # --- フッター部: 終了動作 ---
    gcode += f"G0 Z{config.END_Z:.2f} F{config.F_SPEED}\n"                       # ノズルを安全高さへ退避
    gcode += f"G0 X{config.END_X:.2f} Y{config.END_Y:.2f} F{config.F_SPEED}\n"  # プレートが手前に来る位置へ移動
    gcode += "M84\n"             # モーターをオフ
    return gcode


def save_gcode(pages: list[dict], grid_size: int, file_path: str = "output_route.gcode") -> None:
    """
    Gコードを生成してファイルに保存する。

    Args:
        pages:     レイヤーデータのリスト
        grid_size: 全レイヤー共通のグリッドサイズ
        file_path: 出力先ファイルパス（デフォルト: output_route.gcode）
    """
    content = build_gcode(pages, grid_size)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"積み重ねG-codeを生成しました: {os.path.abspath(file_path)}")
