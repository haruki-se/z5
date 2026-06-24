import tkinter as tk
from tkinter import messagebox
import config
import gcode
import octoprint

ERASER      = "__eraser__"
EMPTY_COLOR = "#c8c8c8"   # 未配置セルの色（グレー）
GRID_LINE   = "#cccccc"
ACCENT      = "#ff9900"
PANEL_BG    = "#f9f9f9"
SEP_COLOR = "#dddddd"

COLOR_LABELS = {"white": "白", "pink": "ピンク", "yellow": "黄色"}


class DrawingApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("金太郎飴 お絵かきボード")
        master.configure(bg=PANEL_BG)
        master.resizable(False, False)

        self.canvas_px  = 480
        self.grid_size  = config.GRID_SIZE_DEFAULT
        self.cell_size  = self.canvas_px // self.grid_size
        self.current_color = config.COLORS[0]
        self.pages: list[dict] = []
        self.current_page  = 0
        self.route_visible = False

        self._build_ui()
        self._bind_keys()
        self.apply_grid_size()
        self.set_color(config.COLORS[0])

    # ─── UI構築 ────────────────────────────────────────────────────

    def _build_ui(self):
        # ── ツールバー
        toolbar = tk.Frame(self.master, bg=PANEL_BG, pady=6)
        toolbar.pack(fill=tk.X, padx=12)

        tk.Label(toolbar, text="マス目数:", bg=PANEL_BG, font=("", 10)).pack(side=tk.LEFT, padx=(0, 4))
        self.grid_size_var = tk.IntVar(value=self.grid_size)
        tk.Spinbox(
            toolbar,
            from_=config.GRID_SIZE_MIN, to=config.GRID_SIZE_MAX,
            textvariable=self.grid_size_var,
            width=4, font=("", 11),
            command=self.apply_grid_size,
        ).pack(side=tk.LEFT)
        tk.Button(toolbar, text="適用", command=self.apply_grid_size, padx=6).pack(side=tk.LEFT, padx=4)

        # ── 3カラムメインエリア
        main = tk.Frame(self.master, bg=PANEL_BG)
        main.pack(padx=12, pady=(0, 6))

        self._build_left_panel(main)
        self._build_canvas(main)
        self._build_right_panel(main)

        # ── ステータスバー
        self.status_var = tk.StringVar()
        tk.Label(
            self.master, textvariable=self.status_var,
            bg="#e8e8e8", anchor=tk.W, padx=10, pady=3, font=("", 9),
        ).pack(fill=tk.X)

    def _build_left_panel(self, parent):
        panel = tk.Frame(parent, bg=PANEL_BG, padx=10, pady=12, relief=tk.GROOVE, bd=1)
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        tk.Label(panel, text="カラー", bg=PANEL_BG, font=("", 9, "bold")).pack(pady=(0, 6))

        self.color_buttons: dict[str, tk.Button] = {}
        for i, name in enumerate(config.COLORS, start=1):
            btn = tk.Button(
                panel,
                text=f"[{i}] {COLOR_LABELS[name]}",
                bg=name,
                width=8, pady=6,
                relief=tk.RAISED, bd=2,
                font=("", 10),
                command=lambda c=name: self.set_color(c),
            )
            btn.pack(pady=3)
            self.color_buttons[name] = btn

        tk.Frame(panel, bg=SEP_COLOR, height=1).pack(fill=tk.X, pady=8)

        self.eraser_btn = tk.Button(
            panel,
            text="[E] 消しゴム",
            width=8, pady=6,
            relief=tk.RAISED, bd=2,
            font=("", 10),
            command=lambda: self.set_color(ERASER),
        )
        self.eraser_btn.pack(pady=3)

    def _build_canvas(self, parent):
        frame = tk.Frame(parent, bg=PANEL_BG)
        frame.pack(side=tk.LEFT)

        self.canvas = tk.Canvas(
            frame,
            width=self.canvas_px, height=self.canvas_px,
            bg="white",
            highlightthickness=1, highlightbackground="#aaaaaa",
            cursor="pencil",
        )
        self.canvas.pack()
        self.canvas.bind("<B1-Motion>", self._on_paint)
        self.canvas.bind("<Button-1>",  self._on_paint)
        self.canvas.bind("<B3-Motion>", self._on_erase)   # 右ドラッグで消しゴム
        self.canvas.bind("<Button-3>",  self._on_erase)   # 右クリックで消しゴム

    def _build_right_panel(self, parent):
        panel = tk.Frame(parent, bg=PANEL_BG, padx=10, pady=12, relief=tk.GROOVE, bd=1)
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))

        # ページナビ
        tk.Label(panel, text="デザイン", bg=PANEL_BG, font=("", 9, "bold")).pack(pady=(0, 4))
        nav = tk.Frame(panel, bg=PANEL_BG)
        nav.pack()
        tk.Button(nav, text="◀", width=3, command=self.prev_page).pack(side=tk.LEFT)
        self.page_label = tk.Label(nav, text="", bg=PANEL_BG, width=7, font=("", 10))
        self.page_label.pack(side=tk.LEFT)
        tk.Button(nav, text="▶", width=3, command=self.next_page).pack(side=tk.LEFT)

        tk.Frame(panel, bg=SEP_COLOR, height=1).pack(fill=tk.X, pady=10)

        btn = dict(width=13, pady=5, font=("", 9))
        tk.Button(panel, text="前ページをコピー",   command=self.copy_prev_page,  **btn).pack(pady=3)
        self.route_btn = tk.Button(panel, text="ルートを表示", command=self.toggle_route_visibility, **btn)
        self.route_btn.pack(pady=3)
        tk.Button(panel, text="このページをリセット", command=self.reset_all, **btn).pack(pady=3)

        tk.Frame(panel, bg=SEP_COLOR, height=1).pack(fill=tk.X, pady=10)

        tk.Button(panel, text="G-code 生成",   command=self.calculate_and_generate_gcode, **btn).pack(pady=3)
        tk.Button(
            panel, text="生成してプリント",
            command=self.generate_and_print,
            bg=ACCENT, fg="white", **btn,
        ).pack(pady=3)

    def _bind_keys(self):
        self.master.bind("<Left>",  lambda e: self.prev_page())
        self.master.bind("<Right>", lambda e: self.next_page())
        for i, name in enumerate(config.COLORS, start=1):
            self.master.bind(str(i), lambda e, c=name: self.set_color(c))
        self.master.bind("e", lambda e: self.set_color(ERASER))
        self.master.bind("E", lambda e: self.set_color(ERASER))

    # ─── グリッド構築 ──────────────────────────────────────────────

    def _calculate_max_pages(self):
        return gcode.calc_layout(config.GRID_SIZE_MIN)["max_pages"]

    def _initialize_pages(self):
        self.pages = [{"white": [], "pink": [], "yellow": []} for _ in range(self.max_pages)]

    def _update_page_label(self):
        self.page_label.config(text=f"{self.current_page + 1} / {self.max_pages}")

    def apply_grid_size(self):
        try:
            new_size = int(self.grid_size_var.get())
        except (ValueError, AttributeError):
            return
        if not (config.GRID_SIZE_MIN <= new_size <= config.GRID_SIZE_MAX):
            return

        self.grid_size = new_size
        self.cell_size = self.canvas_px // self.grid_size
        self.max_pages = self._calculate_max_pages()

        if not self.pages:
            self._initialize_pages()

        self.current_page = 0
        self._update_page_label()
        self.cells = [[None] * self.grid_size for _ in range(self.grid_size)]
        self._create_grid()

    def _create_grid(self):
        self.canvas.delete("all")
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                x, y = c * self.cell_size, r * self.cell_size
                self.cells[r][c] = self.canvas.create_rectangle(
                    x, y, x + self.cell_size, y + self.cell_size,
                    outline=GRID_LINE, fill=EMPTY_COLOR,
                )
        self._update_canvas_colors()

    def _update_canvas_colors(self):
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.cells[r][c] is not None:
                    self.canvas.itemconfig(self.cells[r][c], fill=EMPTY_COLOR)
        for color, cells in self.pages[self.current_page].items():
            for r, c in cells:
                if r < self.grid_size and c < self.grid_size:
                    self.canvas.itemconfig(self.cells[r][c], fill=color)
        self._clear_route_lines()

    # ─── 描画イベント ──────────────────────────────────────────────

    def _get_cell(self, event):
        c = event.x // self.cell_size
        r = event.y // self.cell_size
        if 0 <= r < self.grid_size and 0 <= c < self.grid_size:
            return r, c
        return None

    def _on_paint(self, event):
        cell = self._get_cell(event)
        if cell is None:
            return
        r, c = cell
        if self.current_color == ERASER:
            self._erase_cell(r, c)
        else:
            self._paint_cell(r, c, self.current_color)
        if self.route_visible:
            self._draw_route()

    def _on_erase(self, event):
        cell = self._get_cell(event)
        if cell is None:
            return
        self._erase_cell(*cell)

    def _paint_cell(self, r: int, c: int, color: str):
        dat = self.pages[self.current_page]
        for clr in config.COLORS:
            if (r, c) in dat[clr]:
                dat[clr].remove((r, c))
        dat[color].append((r, c))
        self.canvas.itemconfig(self.cells[r][c], fill=color)

    def _erase_cell(self, r: int, c: int):
        dat = self.pages[self.current_page]
        for clr in config.COLORS:
            if (r, c) in dat[clr]:
                dat[clr].remove((r, c))
        self.canvas.itemconfig(self.cells[r][c], fill=EMPTY_COLOR)

    # ─── ルート可視化 ──────────────────────────────────────────────

    def toggle_route_visibility(self):
        self.route_visible = not self.route_visible
        if self.route_visible:
            self._draw_route()
            self.route_btn.config(text="ルートを非表示")
        else:
            self._clear_route_lines()
            self.route_btn.config(text="ルートを表示")

    def _draw_route(self):
        self._clear_route_lines()
        half = self.cell_size / 2
        lx, ly = -1.0, -1.0
        for r in range(self.grid_size):
            cols = range(self.grid_size) if r % 2 == 0 else range(self.grid_size - 1, -1, -1)
            for c in cols:
                cx = c * self.cell_size + half
                cy = r * self.cell_size + half
                if lx >= 0:
                    self.canvas.create_line(lx, ly, cx, cy, fill="red", width=2, tags="route_line", arrow=tk.LAST)
                lx, ly = cx, cy

    def _clear_route_lines(self):
        self.canvas.delete("route_line")

    # ─── ページ操作 ────────────────────────────────────────────────

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_page_label()
            self._update_canvas_colors()
            if self.route_visible:
                self._draw_route()

    def next_page(self):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self._update_page_label()
            self._update_canvas_colors()
            if self.route_visible:
                self._draw_route()

    def copy_prev_page(self):
        if self.current_page > 0:
            self.pages[self.current_page] = {k: v[:] for k, v in self.pages[self.current_page - 1].items()}
            self._update_canvas_colors()
            if self.route_visible:
                self._draw_route()

    def reset_all(self):
        self.pages[self.current_page] = {k: [] for k in config.COLORS}
        self._update_canvas_colors()

    # ─── 色選択 ────────────────────────────────────────────────────

    def set_color(self, color: str):
        for btn in self.color_buttons.values():
            btn.config(relief=tk.RAISED, bd=2)
        self.eraser_btn.config(relief=tk.RAISED, bd=2)

        self.current_color = color

        if color == ERASER:
            self.eraser_btn.config(relief=tk.SUNKEN, bd=3)
            self.status_var.set("ツール: 消しゴム  ｜  右クリック・右ドラッグでも消去できます")
        else:
            self.color_buttons[color].config(relief=tk.SUNKEN, bd=3)
            self.status_var.set(
                f"カラー: {COLOR_LABELS[color]}  ｜  "
                "[1/2/3] 色切替  [E] 消しゴム  [←/→] ページ移動  右クリック: 消去"
            )

    # ─── G-code / プリント ─────────────────────────────────────────

    def calculate_and_generate_gcode(self):
        gcode.save_gcode(self.pages, self.grid_size, "output_plate.gcode")
        self.status_var.set("G-code を output_plate.gcode に保存しました")

    def generate_and_print(self):
        # 全ページ空チェック
        has_any = any(any(cells for cells in page.values()) for page in self.pages)
        if not has_any:
            messagebox.showerror("エラー", "デザインが描かれていません。\n白・ピンク・黄色のいずれかのマスを塗ってからプリントしてください。")
            return

        # 塗り残しチェック（描画済みページに限定）
        total_cells = self.grid_size * self.grid_size
        for i, page in enumerate(self.pages):
            painted = sum(len(cells) for cells in page.values())
            if painted == 0:
                continue
            if painted < total_cells:
                self.current_page = i
                self._update_page_label()
                self._update_canvas_colors()
                messagebox.showerror(
                    "エラー",
                    f"デザイン {i + 1} に塗られていないマスがあります。\nすべてのマスを塗ってからプリントしてください。",
                )
                return

        gcode.save_gcode(self.pages, self.grid_size, "output_plate.gcode")
        try:
            ref = octoprint.upload_and_print("output_plate.gcode")
            messagebox.showinfo("プリント開始", f"OctoPrint に送信しました。\nプリントを開始します。\n\n{ref}")
            self.status_var.set("OctoPrint に送信しました")
        except RuntimeError as e:
            messagebox.showerror("送信エラー", str(e))
