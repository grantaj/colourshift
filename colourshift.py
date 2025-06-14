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

        self.base_display = tk.Canvas(self.top_frame, width=60, height=60, highlightthickness=1, highlightbackground='black')
        self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, outline='')
        self.base_display.bind("<Button-1>", lambda e: self.pick_base_color())
        self.base_display.pack(side=tk.LEFT, padx=5)

        self.surround_display = tk.Canvas(self.top_frame, width=60, height=60, highlightthickness=1, highlightbackground='black')
        self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, outline='')
        self.surround_display.bind("<Button-1>", lambda e: self.pick_surround_color())
        self.surround_display.pack(side=tk.LEFT, padx=5)

        
        self.solve_btn = tk.Button(self.top_frame, text="Solve Maximal Shift", command=self.solve)
        self.solve_btn.pack(side=tk.LEFT, padx=10)

    def pick_base_color(self):
        color = colorchooser.askcolor(title="Pick Base Color")
        if color[1]:
            self.base_color = color[1]
            self.base_display.delete("all")
            self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, outline='')

    def pick_surround_color(self):
        color = colorchooser.askcolor(title="Pick Surround Color")
        if color[1]:
            self.original_surround = color[1]
            self.surround_display.delete("all")
            self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, outline='')

    def set_surround(self, hex_color):
        self.original_surround = hex_color
        self.surround_display.delete("all")
        self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, outline='')

    def handle_patch_click(self, hex_color, event=None):
        comparison_window = tk.Toplevel(self.root)
        comparison_window.title("Perceptual Shift Comparison")
        comparison_window.geometry("600x300")

        base_rgb = hex_to_rgb(self.base_color)
        left_surround = self.original_surround
        right_surround = hex_color

        left_canvas = tk.Canvas(comparison_window, width=300, height=300)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_canvas.create_rectangle(0, 0, 300, 300, fill=left_surround, outline="")
        left_canvas.create_rectangle(125, 125, 175, 175, fill=self.base_color, outline="black")

        right_canvas = tk.Canvas(comparison_window, width=300, height=300)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_canvas.create_rectangle(0, 0, 300, 300, fill=right_surround, outline="")
        right_canvas.create_rectangle(125, 125, 175, 175, fill=self.base_color, outline="black")

    def solve(self):
        base_rgb = hex_to_rgb(self.base_color)
        surround_rgb = hex_to_rgb(self.original_surround)
        results = compute_appearance_difference(base_rgb, surround_rgb)

        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        for i, (rgb, dE) in enumerate(results):
            hex_col = rgb_to_hex(rgb)

            patch_frame = tk.Frame(self.preview_frame)
            patch_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)

            from functools import partial
            canvas = tk.Canvas(patch_frame, width=100, height=100, highlightthickness=1, highlightbackground="black")
            canvas.create_rectangle(0, 0, 100, 100, fill=hex_col, outline="")
            canvas.bind("<Button-1>", partial(self.handle_patch_click, hex_col))
            canvas.pack()

            label = tk.Label(patch_frame, text=f"ΔAppearance = {dE:.2f}", bg="white", fg="black")
            label.pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = ColourShiftApp(root)
    root.mainloop()
