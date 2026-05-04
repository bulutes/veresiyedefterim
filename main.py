# -*- coding: utf-8 -*-
"""
CariiDefterim - Ana Başlatıcı
==============================
Uygulamayı başlatan ana dosya.

Kullanım:
    python main.py

PyInstaller ile paketleme:
    pyinstaller --onefile --windowed --name CariiDefterim main.py
"""

import tkinter as tk
from ui import CariDefterimApp


def main():
    """Uygulamayı başlatır."""
    root = tk.Tk()

    # Uygulama simgesi (varsa)
    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass

    app = CariDefterimApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
