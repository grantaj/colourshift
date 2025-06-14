import tkinter as tk
from tkinter import colorchooser
import numpy as np
import colour
from colour.appearance import XYZ_to_CIECAM02
from colour.models.cam02_ucs import JMh_CIECAM02_to_CAM02UCS
from colour.difference import delta_E_CAM02UCS


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

    vc = colour.VIEWING_CONDITIONS_CIECAM02['Average']
    Y_b = 20
    L_A = 64

    base_spec = XYZ_to_CIECAM02(base_XYZ, original_surround_XYZ, Y_b, L_A, surround=vc)
    base_JMh = [base_spec.J, base_spec.M, base_spec.h]
    base_UCS = JMh_CIECAM02_to_CAM02UCS(base_JMh)

    results = []
    for r in np.linspace(0, 1, 12):
        for g in np.linspace(0, 1, 12):
            for b in np.linspace(0, 1, 12):
                candidate_rgb = [r, g, b]
                try:
                    surround_XYZ = rgb_to_XYZ(candidate_rgb)
                    candidate_spec = XYZ_to_CIECAM02(base_XYZ, surround_XYZ, Y_b, L_A, surround=vc)
                    candidate_JMh = [candidate_spec.J, candidate_spec.M, candidate_spec.h]
                    candidate_UCS = JMh_CIECAM02_to_CAM02UCS(candidate_JMh)
                    dE = delta_E_CAM02UCS(base_UCS, candidate_UCS)
                    if not np.isfinite(dE):
                        continue
                    results.append((candidate_rgb, dE))
                except Exception:
                    continue

    results.sort(key=lambda x: -x[1])
    return results[:3]

class ColourShiftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ColourShift")
        self.base_color = "#950000"
        self.original_surround = "#964301"

        self.top_frame = tk.Frame(root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.preview_frame = tk.Frame(root, bg="#808080")
        self.preview_frame.pack(expand=True, fill=tk.BOTH)

        self.base_display = tk.Canvas(self.top_frame, width=60, height=60, highlightthickness=1, highlightbackground='black')
        self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, width=0)
        self.base_display.bind("<Button-1>", lambda e: self.pick_base_color())
        self.base_display.pack(side=tk.LEFT, padx=5)

        self.surround_display = tk.Canvas(self.top_frame, width=60, height=60, highlightthickness=1, highlightbackground='black')
        self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, width=0)
        self.surround_display.bind("<Button-1>", lambda e: self.pick_surround_color())
        self.surround_display.pack(side=tk.LEFT, padx=5)

        self.solve_btn = tk.Button(self.top_frame, text="Solve Maximal Shift", command=self.solve)
        self.solve_btn.pack(side=tk.LEFT, padx=10)

    def pick_base_color(self):
        color = colorchooser.askcolor(title="Pick Base Color")
        if color[1]:
            self.base_color = color[1]
            self.base_display.delete("all")
            self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, width=0)

    def pick_surround_color(self):
        color = colorchooser.askcolor(title="Pick Surround Color")
        if color[1]:
            self.original_surround = color[1]
            self.surround_display.delete("all")
            self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, width=0)

    def set_surround(self, hex_color):
        self.original_surround = hex_color
        self.surround_display.delete("all")
        self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, width=0)

    def handle_patch_click(self, hex_color, event=None):
        comparison_window = tk.Toplevel(self.root)
        comparison_window.title("Perceptual Shift Comparison")

        left_canvas = tk.Canvas(comparison_window, highlightthickness=0, bd=0)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_canvas = tk.Canvas(comparison_window, highlightthickness=0, bd=0)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def draw_comparison():
            comparison_window.update_idletasks()
            w = comparison_window.winfo_width()
            h = comparison_window.winfo_height()
            half_w = w // 2

            for canvas in (left_canvas, right_canvas):
                canvas.delete("all")
            w = 50
            left_canvas.create_rectangle(0, 0, half_w, h, fill=self.original_surround, width=0)
            left_canvas.create_rectangle(half_w//2 - w, h//2 - w, half_w//2 + w, h//2 + w, fill=self.base_color, width=0)

            right_canvas.create_rectangle(0, 0, half_w, h, fill=hex_color, width=0)
            right_canvas.create_rectangle(half_w//2 - w, h//2 - w, half_w//2 + w, h//2 + w, fill=self.base_color, width=0)

        def schedule_draw(_event=None):
            comparison_window.after_idle(draw_comparison)

        comparison_window.bind("<Configure>", schedule_draw)
        draw_comparison()

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
            canvas.create_rectangle(0, 0, 100, 100, fill=hex_col, width=0)
            canvas.bind("<Button-1>", partial(self.handle_patch_click, hex_col))
            canvas.pack()

            label = tk.Label(patch_frame, text=f"ΔAppearance = {dE:.2f}", bg="white", fg="black")
            label.pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = ColourShiftApp(root)
    root.mainloop()
