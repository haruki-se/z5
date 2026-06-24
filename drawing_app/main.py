# main.py - エントリーポイント
#
# このファイルがアプリの起動口です。
# VSCode の「実行」ボタンはここで押してください。
#
# 起動すると DrawingApp ウィンドウが開きます。

import sys
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

import tkinter as tk
from app import DrawingApp

if __name__ == "__main__":
    root = tk.Tk()          # tkinter のメインウィンドウを生成
    app = DrawingApp(root)  # アプリ本体を初期化
    root.mainloop()         # イベントループ開始（ウィンドウを閉じるまで待機）