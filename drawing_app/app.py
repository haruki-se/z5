import tkinter as tk
from tkinter import messagebox
import config
import gcode
import octoprint

class DrawingApp:
    def __init__(self, master):
        self.master = master
        master.title("お絵かきボード - 自動レイアウトモード")

        # 基本設定
        self.canvas_size = 400
        self.grid_size = 3  # 初期値 3x3
        self.cell_size = self.canvas_size // self.grid_size
        self.current_color = "white"
        self.route_visible = False
        
        self.pages = []
        self.current_page = 0

        # === UI構成: 上部設定エリア ===
        setting_frame = tk.Frame(master)
        setting_frame.pack(pady=5)
        tk.Label(setting_frame, text="1デザインのマス目数 (最小3, 最大16):").pack(side=tk.LEFT, padx=5)
        
        self.grid_size_var = tk.StringVar(value=str(self.grid_size)) 
        self.grid_size_entry = tk.Entry(setting_frame, textvariable=self.grid_size_var, width=5)
        self.grid_size_entry.pack(side=tk.LEFT, padx=5)
        
        apply_button = tk.Button(setting_frame, text="適用", command=self.apply_grid_size)
        apply_button.pack(side=tk.LEFT, padx=5)
        
        # キャンバス
        self.canvas = tk.Canvas(master, width=self.canvas_size+10, height=self.canvas_size+10, bg="white")
        self.canvas.pack(pady=10)


        # 初期化実行（max_pagesの計算を含む）
        self.apply_grid_size()

        # イベントバインド
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<Button-1>", self.paint)
        
        # デザイン切り替えコントロール
        top_button_frame = tk.Frame(master)
        top_button_frame.pack(pady=5)
        tk.Button(top_button_frame, text="← 前のデザイン", command=self.prev_page).pack(side=tk.LEFT, padx=5)
        self.page_label = tk.Label(top_button_frame, text="")
        self.page_label.pack(side=tk.LEFT, padx=5)
        tk.Button(top_button_frame, text="次のデザイン →", command=self.next_page).pack(side=tk.LEFT, padx=5)
        self._update_page_label()

        # カラー/アクションボタン
        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)
        self.colors = config.COLORS
        self.color_buttons = {}
        for color_name in self.colors:
            btn = tk.Button(button_frame, text="", bg=color_name, width=2, command=lambda c=color_name: self.set_color(c))
            btn.pack(side=tk.LEFT, padx=3)
            self.color_buttons[color_name] = btn

        tk.Button(button_frame, text="全リセット", command=self.reset_all).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="G-code生成", command=self.calculate_and_generate_gcode).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="生成してプリント", command=self.generate_and_print, bg="#ff9900", fg="white").pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="前のデザインをコピー", command=self.copy_prev_page).pack(side=tk.LEFT, padx=10)
        self.show_route_button = tk.Button(button_frame, text="ルートの可視化", command=self.toggle_route_visibility)
        self.show_route_button.pack(side=tk.LEFT, padx=10)
        
        self.set_color(self.current_color)

    def _calculate_max_pages(self):
        return gcode.calc_layout(self.grid_size)["max_pages"]

    def _initialize_pages(self):
        self.pages = [{"white": [], "pink": [], "yellow": []} for _ in range(self.max_pages)]

    def _update_page_label(self):
        self.page_label.config(text=f"デザイン: {self.current_page + 1}/{self.max_pages}")

    def apply_grid_size(self):
        try:
            new_size = int(self.grid_size_var.get())
            if 3 <= new_size <= 16:
                self.grid_size = new_size
                self.cell_size = self.canvas_size // self.grid_size
                
                self.max_pages = self._calculate_max_pages()
                
                self._initialize_pages()
                self.current_page = 0
                if hasattr(self, 'page_label'): self._update_page_label()
                
                self.cells = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]
                self._create_grid()
                print(f"1デザイン{new_size}x{new_size}を最大{self.max_pages}個配置可能（Yオフセット:{config.GLOBAL_Y_OFFSET}mm）として設定しました。")
        except ValueError: pass

    def _create_grid(self):
        self.canvas.delete("all")
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                x, y = col * self.cell_size, row * self.cell_size
                self.cells[row][col] = self.canvas.create_rectangle(x, y, x+self.cell_size, y+self.cell_size, outline="gray", fill="white")
        self._update_canvas_colors()
    
    def _update_canvas_colors(self):
        for r in range(self.grid_size):
            for c in range(self.grid_size): 
                if self.cells[r][c] is not None:
                    self.canvas.itemconfig(self.cells[r][c], fill="white")
        for color, cells in self.pages[self.current_page].items():
            for r, c in cells: 
                if r < self.grid_size and c < self.grid_size:
                    self.canvas.itemconfig(self.cells[r][c], fill=color)
        self._clear_route_lines()

    def toggle_route_visibility(self):
        self.route_visible = not self.route_visible
        if self.route_visible:
            self._draw_page_route()
            self.show_route_button.config(text="ルートを非表示")
        else:
            self._clear_route_lines()
            self.show_route_button.config(text="ルートの可視化")

    def _clear_route_lines(self): self.canvas.delete("route_line")

    def _draw_page_route(self):
        self._clear_route_lines()
        route = self._generate_snake_route()
        lx, ly = -1, -1
        for r, c in route:
            cx, cy = c * self.cell_size + self.cell_size / 2, r * self.cell_size + self.cell_size / 2
            if lx != -1: self.canvas.create_line(lx, ly, cx, cy, fill="red", width=2, tags="route_line", arrow=tk.LAST)
            lx, ly = cx, cy

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_page_label()
            self._update_canvas_colors()
            if self.route_visible: self._draw_page_route()

    def next_page(self):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self._update_page_label()
            self._update_canvas_colors()
            if self.route_visible: self._draw_page_route()

    def copy_prev_page(self):
        if self.current_page > 0:
            self.pages[self.current_page] = {k: v[:] for k, v in self.pages[self.current_page-1].items()}
            self._update_canvas_colors()
            if self.route_visible: self._draw_page_route()

    def paint(self, event):
        c, r = event.x // self.cell_size, event.y // self.cell_size
        if 0 <= r < self.grid_size and 0 <= c < self.grid_size:
            dat = self.pages[self.current_page]
            for clr in self.colors:
                if (r, c) in dat[clr]: dat[clr].remove((r, c))
            dat[self.current_color].append((r, c))
            self.canvas.itemconfig(self.cells[r][c], fill=self.current_color)
            if self.route_visible: self._draw_page_route()

    def set_color(self, color):
        if self.current_color in self.color_buttons: self.color_buttons[self.current_color].config(relief=tk.RAISED)
        self.current_color = color
        if color in self.color_buttons: self.color_buttons[color].config(relief=tk.SUNKEN)

    def reset_all(self):
        self.pages[self.current_page] = {k: [] for k in self.colors}
        self._update_canvas_colors()

    def _generate_snake_route(self):
        route = []
        for r in range(self.grid_size):
            cols = range(self.grid_size) if r % 2 == 0 else range(self.grid_size-1, -1, -1)
            for c in cols: route.append((r, c))
        return route

    def calculate_and_generate_gcode(self):
        file_path = "output_plate.gcode"
        gcode.save_gcode(self.pages, self.grid_size, file_path)

    def generate_and_print(self):
        file_path = "output_plate.gcode"
        gcode.save_gcode(self.pages, self.grid_size, file_path)
        try:
            ref = octoprint.upload_and_print(file_path)
            messagebox.showinfo("プリント開始", f"OctoPrint に送信しました。\nプリントを開始します。\n\n{ref}")
        except RuntimeError as e:
            messagebox.showerror("送信エラー", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = DrawingApp(root)
    root.mainloop()