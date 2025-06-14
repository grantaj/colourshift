import tkinter as tk
from tkinter import colorchooser
import numpy as np
import colour

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4)]

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(int(255*x) for x in rgb))

def rgb_to_XYZ(rgb):
    return colour.sRGB_to_XYZ(rgb)

def compute_appearance_difference(base_rgb, original_surround_rgb):
    base_XYZ = rgb_to_XYZ(base_rgb)
    original_surround_XYZ = rgb_to_XYZ(original_surround_rgb)

    vc = colour.appearance.VIEWING_CONDITIONS_CIECAM02["Average"]
    appearance_1 = colour.appearance.XYZ_to_CIECAM02(base_XYZ, original_surround_XYZ, L_A=64, Y_b=20, surround=vc)
    J1, C1, h1 = appearance_1.J, appearance_1.C, appearance_1.h

    results = []
    for r in np.linspace(0, 1, 12):
        for g in np.linspace(0, 1, 12):
            for b in np.linspace(0, 1, 12):
                surround_rgb = [r, g, b]
                surround_XYZ = rgb_to_XYZ(surround_rgb)

                try:
                    appearance_2 = colour.appearance.XYZ_to_CIECAM02(
                        base_XYZ, surround_XYZ, L_A=64, Y_b=20, surround=vc
                    )
                    J2, C2, h2 = appearance_2.J, appearance_2.C, appearance_2.h

                    if any(v is None or not np.isfinite(v) for v in [J1, C1, h1, J2, C2, h2]):
                        continue

                    h_diff = min(abs(h1 - h2), 360 - abs(h1 - h2))

                    J_diff = np.clip(J1 - J2, -1e3, 1e3)
                    C_diff = np.clip(C1 - C2, -1e3, 1e3)
                    h_diff = np.clip(h_diff, 0, 360)

                    dE = np.sqrt(J_diff**2 + C_diff**2 + h_diff**2)
                    if not np.isfinite(dE) or dE > 1e4:
                        continue
                    results.append((surround_rgb, dE))

                except Exception:
                    continue  # Skip colors that cause math errors

    results.sort(key=lambda x: -x[1])
    return results[:3]

class ColourShiftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ColourShift")
        self.base_color = "#ff0000"
        self.original_surround = "#808080"

        self.top_frame = tk.Frame(root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.preview_frame = tk.Frame(root, bg="#808080")
        self.preview_frame.pack(expand=True, fill=tk.BOTH)

        self.base_display = tk.Label(self.top_frame, text=f"Base: {self.base_color}", bg=self.base_color, fg="white", width=15)
        self.base_display.pack(side=tk.LEFT, padx=5)

        self.surround_display = tk.Label(self.top_frame, text=f"Surround: {self.original_surround}", bg=self.original_surround, fg="white", width=15)
        self.surround_display.pack(side=tk.LEFT, padx=5)

        self.base_btn = tk.Button(self.top_frame, text="Pick Base Color", command=self.pick_base_color)
        self.base_btn.pack(side=tk.LEFT, padx=10)

        self.surround_btn = tk.Button(self.top_frame, text="Pick Surround Color", command=self.pick_surround_color)
        self.surround_btn.pack(side=tk.LEFT, padx=10)

        self.solve_btn = tk.Button(self.top_frame, text="Solve Maximal Shift", command=self.solve)
        self.solve_btn.pack(side=tk.LEFT, padx=10)

    def pick_base_color(self):
        color = colorchooser.askcolor(title="Pick Base Color")
        if color[1]:
            self.base_color = color[1]
            self.base_display.config(text=f"Base: {self.base_color}", bg=self.base_color)

    def pick_surround_color(self):
        color = colorchooser.askcolor(title="Pick Surround Color")
        if color[1]:
            self.original_surround = color[1]
            self.surround_display.config(text=f"Surround: {self.original_surround}", bg=self.original_surround)

    def solve(self):
        base_rgb = hex_to_rgb(self.base_color)
        surround_rgb = hex_to_rgb(self.original_surround)
        results = compute_appearance_difference(base_rgb, surround_rgb)

        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        for i, (rgb, dE) in enumerate(results):
            patch = tk.Frame(self.preview_frame, bg=rgb_to_hex(rgb), width=150, height=150)
            patch.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
            tk.Label(patch, text=f"ΔAppearance = {dE:.2f}", bg=rgb_to_hex(rgb), fg="white").pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = ColourShiftApp(root)
    root.mainloop()
