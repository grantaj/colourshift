import tkinter as tk
from tkinter import colorchooser
from skimage.color import rgb2lab, deltaE_ciede2000
import numpy as np


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4)]

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(int(255*x) for x in rgb))

def compute_maximal_shifts(base_rgb):
    base_lab = rgb2lab(np.array(base_rgb).reshape(1, 1, 3))
    candidates = []
    for r in np.linspace(0, 1, 12):
        for g in np.linspace(0, 1, 12):
            for b in np.linspace(0, 1, 12):
                rgb = [r, g, b]
                lab = rgb2lab(np.array(rgb).reshape(1, 1, 3))
                delta = deltaE_ciede2000(base_lab, lab)[0][0]
                candidates.append((rgb, delta))
    candidates.sort(key=lambda x: -x[1])
    return candidates[:3]

class ColourShiftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ColourShift")
        self.base_color = "#ff0000"

        self.top_frame = tk.Frame(root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.preview_frame = tk.Frame(root, bg="#808080")
        self.preview_frame.pack(expand=True, fill=tk.BOTH)

        self.color_btn = tk.Button(self.top_frame, text="Choose Base Color", command=self.pick_base_color)
        self.color_btn.pack(side=tk.LEFT, padx=10)

        self.solve_btn = tk.Button(self.top_frame, text="Solve Maximal Shift", command=self.solve)
        self.solve_btn.pack(side=tk.LEFT, padx=10)

    def pick_base_color(self):
        color = colorchooser.askcolor(title="Pick Base Color")
        if color[1]:
            self.base_color = color[1]

    def solve(self):
        base_rgb = hex_to_rgb(self.base_color)
        results = compute_maximal_shifts(base_rgb)

        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        for i, (rgb, delta) in enumerate(results):
            patch = tk.Frame(self.preview_frame, bg=rgb_to_hex(rgb), width=150, height=150)
            patch.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
            tk.Label(patch, text=f"ΔE = {delta:.2f}", bg=rgb_to_hex(rgb), fg="white").pack()


if __name__ == "__main__":
    root = tk.Tk()
    app = ColourShiftApp(root)
    root.mainloop()
