"""Entry point for the Shannon capacity tkinter application."""

import tkinter as tk
from tkinter import ttk

from ui import ShannonApp


def main():
    root = tk.Tk()
    root.title("Shannon-Hartley Channel Capacity")
    root.geometry("820x620")
    root.minsize(720, 520)

    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")

    ShannonApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
