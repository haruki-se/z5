# canvas_view.py - キャンバス描画・グリッド管理・ルート可視化
#
# tkinter.Canvas をラップした CanvasView クラスを定義します。
# 「何を描くか」は DrawingApp（app.py）が決め、
# 「どう描くか」はこのクラスが担当するという役割分担です。
#
# CanvasView はページデータや状態を自分では持ちません。
# DrawingApp から都度データを受け取って描画するだけなので、
# 将来的にキャンバスを複数にしたり差し替えたりしやすい設計です。

import tkinter as tk
import config
from gcode import generate_snake_route


class CanvasView:
    """
    tkinter.Canvas のラッパークラス。
    グリッドの描画・セル色の更新・スネークルートの可視化を担当する。
    """

    def __init__(self, master: tk.Widget):
        """
        キャンバスウィジェットを生成して master に配置する。

        Args:
            master: 親ウィジェット（通常は tk.Tk のルートウィンドウ）
        """
        initial_size = config.GRID_SIZE_DEFAULT * config.CELL_PIXEL_SIZE + 1
        self.canvas = tk.Canvas(
            master,
            width=initial_size,
            height=initial_size,
            bg="white",
            highlightthickness=0,
        )
        self.canvas.pack(pady=10)

        self._grid_size = 0   # 現在のグリッドの一辺マス数
        self._cell_size = 0   # 1セルのピクセルサイズ
        # _cells[row][col] = canvas 上の矩形アイテムの ID
        self._cells: list[list[int | None]] = []

    # ------------------------------------------------------------------
    # グリッド構築
    # ------------------------------------------------------------------

    def build_grid(self, grid_size: int) -> None:
        """
        指定サイズでグリッドを再構築する。
        既存の描画内容はすべて削除されてリセットされる。

        Args:
            grid_size: グリッドの一辺のマス数
        """
        self._grid_size = grid_size
        self._cell_size = config.CELL_PIXEL_SIZE

        canvas_size = self._grid_size * self._cell_size + 1
        self.canvas.config(width=canvas_size, height=canvas_size)

        self.canvas.delete("all")  # 既存の全描画要素を削除
        self._cells = [[None] * grid_size for _ in range(grid_size)]

        # グリッド線と塗りつぶし領域（矩形）を生成
        for row in range(grid_size):
            for col in range(grid_size):
                x = col * self._cell_size
                y = row * self._cell_size
                self._cells[row][col] = self.canvas.create_rectangle(
                    x, y,
                    x + self._cell_size, y + self._cell_size,
                    outline="blue",   # グリッド線の色
                )

    # ------------------------------------------------------------------
    # セル色の更新
    # ------------------------------------------------------------------

    def update_colors(self, page_data: dict) -> None:
        """
        ページデータに基づいてキャンバス全体のセル色を更新する。
        ページ切り替えや全リセット後に呼び出す。
        ルート線も同時に消去する（必要なら呼び出し元で再描画すること）。

        Args:
            page_data: {"white": [(r,c), ...], "pink": [...], "yellow": [...]}
        """
        # まず全セルを白にリセット
        for row in range(self._grid_size):
            for col in range(self._grid_size):
                item = self._cells[row][col]
                if item is not None:
                    self.canvas.itemconfig(item, fill="gray")  # デフォルトは白（背景色）にするため、グリッド線と同じ色で塗りつぶす

        # ページデータの色情報を反映
        for color, cell_list in page_data.items():
            for row, col in cell_list:
                # グリッドサイズ変更後の古いデータが混入しないよう範囲チェック
                if row < self._grid_size and col < self._grid_size:
                    self.canvas.itemconfig(self._cells[row][col], fill=color)

        self._clear_route_lines()  # ルート線を消去

    def paint_cell(self, row: int, col: int, color: str) -> None:
        """
        単一セルの色を即時更新する。
        クリック・ドラッグ中の高速な描画更新に使用する。

        Args:
            row:   対象セルの行インデックス
            col:   対象セルの列インデックス
            color: 塗る色（"white" / "pink" / "yellow"）
        """
        self.canvas.itemconfig(self._cells[row][col], fill=color)

    def get_cell_at(self, pixel_x: int, pixel_y: int) -> tuple[int, int] | None:
        """
        マウスのピクセル座標からグリッドの (row, col) を計算して返す。
        キャンバス外や範囲外の場合は None を返す。

        Args:
            pixel_x: マウスの X 座標（ピクセル）
            pixel_y: マウスの Y 座標（ピクセル）

        Returns:
            (row, col) のタプル、または None
        """
        col = pixel_x // self._cell_size
        row = pixel_y // self._cell_size
        if 0 <= row < self._grid_size and 0 <= col < self._grid_size:
            return row, col
        return None

    # ------------------------------------------------------------------
    # ルート可視化
    # ------------------------------------------------------------------

    def draw_route(self) -> None:
        """
        スネークルートをキャンバス上に赤い矢印付きの線で描画する。
        既存のルート線は描画前に消去される。
        ノズルの動作順序を視覚的に確認するための機能。
        """
        self._clear_route_lines()
        route = generate_snake_route(self._grid_size)
        half = self._cell_size / 2  # セル中心へのオフセット
        prev_x, prev_y = -1.0, -1.0  # 前のセルの中心座標（未初期化は -1 で判定）

        for row, col in route:
            # セル中心のピクセル座標
            cx = col * self._cell_size + half
            cy = row * self._cell_size + half
            if prev_x >= 0:
                # 前のセルから現在のセルへ矢印を描画
                self.canvas.create_line(
                    prev_x, prev_y, cx, cy,
                    fill="red",
                    width=2,
                    tags="route_line",  # タグで一括削除できるようにする
                    arrow=tk.LAST,      # 終点に矢じりを表示
                )
            prev_x, prev_y = cx, cy

    def clear_route(self) -> None:
        """ルート線をすべて消去する。"""
        self._clear_route_lines()

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _clear_route_lines(self) -> None:
        """タグ "route_line" が付いた全描画要素を削除する。"""
        self.canvas.delete("route_line")