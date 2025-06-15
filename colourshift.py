import tkinter as tk
from tkinter import colorchooser, ttk, filedialog
from PIL import Image, ImageDraw
import numpy as np
import colour
from colour.appearance import XYZ_to_CIECAM02
from colour.models.cam02_ucs import JMh_CIECAM02_to_CAM02UCS
from colour.difference import delta_E_CAM02UCS
import warnings
import json

DEBUG = False

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4)]

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(int(255*x) for x in rgb))

def rgb_to_XYZ(rgb):
    return colour.sRGB_to_XYZ(rgb)

def is_valid_JMh(J, M, h):
    return (
        np.isfinite(J) and np.isfinite(M) and np.isfinite(h) and
        0 <= J <= 100 and
        0 <= M <= 100 and
        0 <= h <= 360
    )

def compute_appearance_difference(base_rgb, original_surround_rgb, min_delta=10.0, max_candidates=3):
    base_XYZ = rgb_to_XYZ(base_rgb)
    original_surround_XYZ = rgb_to_XYZ(original_surround_rgb)

    vc = colour.VIEWING_CONDITIONS_CIECAM02['Average']
    Y_b = 20
    L_A = 64

    base_spec = XYZ_to_CIECAM02(base_XYZ, original_surround_XYZ, Y_b, L_A, surround=vc)
    base_JMh = [base_spec.J, base_spec.M, base_spec.h]
    base_UCS = JMh_CIECAM02_to_CAM02UCS(base_JMh)

    if DEBUG is True:
        print("Base JMh:", base_JMh)
        print("Base UCS:", base_UCS)

    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for r in np.linspace(0, 1, 12):
            for g in np.linspace(0, 1, 12):
                for b in np.linspace(0, 1, 12):
                    candidate_rgb = [r, g, b]
                    try:
                        surround_XYZ = rgb_to_XYZ(candidate_rgb)
                        candidate_spec = XYZ_to_CIECAM02(base_XYZ, surround_XYZ, Y_b, L_A, surround=vc)
                        J, M, h = candidate_spec.J, candidate_spec.M, candidate_spec.h
                        if not is_valid_JMh(J, M, h):
                            continue
                        candidate_JMh = [J, M, h]
                        candidate_UCS = JMh_CIECAM02_to_CAM02UCS(candidate_JMh)
                        if not all(np.isfinite(candidate_UCS)):
                            continue
                        shift_dE = delta_E_CAM02UCS(base_UCS, candidate_UCS)
                        if not np.isfinite(shift_dE):
                            continue
                        if DEBUG is True:
                            print(f"Candidate {rgb_to_hex(candidate_rgb)} - JMh: {candidate_JMh}, UCS: {candidate_UCS}, ΔE: {shift_dE:.2f}")
                        candidates.append((candidate_rgb, shift_dE, candidate_UCS))
                    except Exception as e:
                        print(f"Error with {candidate_rgb}: {e}")
                        continue

    candidates.sort(key=lambda x: -x[1])

    filtered = []
    for rgb, shift_dE, ucs in candidates:
        deltas = [delta_E_CAM02UCS(ucs, other_ucs) for _, _, other_ucs in filtered]
        if DEBUG is True:
            print(f"Testing candidate {rgb_to_hex(rgb)} with ΔE distances to existing: {deltas}")
        if all(d >= min_delta for d in deltas):
            filtered.append((rgb, shift_dE, ucs))
        if len(filtered) >= max_candidates:
            break

    return [(rgb, delta_E_CAM02UCS(base_UCS, ucs)) for rgb, _, ucs in filtered]

def find_extreme_shift_colors(fixed_rgb, fixed_as_base, min_delta=10.0, max_candidates=3):
    fixed_XYZ = rgb_to_XYZ(fixed_rgb)
    vc = colour.VIEWING_CONDITIONS_CIECAM02['Average']
    Y_b = 20
    L_A = 64

    candidates = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for r in np.linspace(0, 1, 12):
            for g in np.linspace(0, 1, 12):
                for b in np.linspace(0, 1, 12):
                    test_rgb = [r, g, b]
                    try:
                        test_XYZ = rgb_to_XYZ(test_rgb)
                        if fixed_as_base:
                            base_spec = XYZ_to_CIECAM02(fixed_XYZ, test_XYZ, Y_b, L_A, surround=vc)
                            test_spec = XYZ_to_CIECAM02(fixed_XYZ, fixed_XYZ, Y_b, L_A, surround=vc)
                        else:
                            base_spec = XYZ_to_CIECAM02(test_XYZ, fixed_XYZ, Y_b, L_A, surround=vc)
                            test_spec = XYZ_to_CIECAM02(fixed_XYZ, fixed_XYZ, Y_b, L_A, surround=vc)

                        base_JMh = [base_spec.J, base_spec.M, base_spec.h]
                        test_JMh = [test_spec.J, test_spec.M, test_spec.h]
                        if not (is_valid_JMh(*base_JMh) and is_valid_JMh(*test_JMh)):
                            continue
                        base_UCS = JMh_CIECAM02_to_CAM02UCS(base_JMh)
                        test_UCS = JMh_CIECAM02_to_CAM02UCS(test_JMh)
                        if not all(np.isfinite(test_UCS)):
                            continue
                        shift_dE = delta_E_CAM02UCS(base_UCS, test_UCS)
                        if not np.isfinite(shift_dE):
                            continue
                        candidates.append((test_rgb, shift_dE))
                    except Exception:
                        continue
    candidates.sort(key=lambda x: -x[1])
    filtered = []
    for rgb, dE in candidates:
        deltas = []
        for r, _ in filtered:
            spec1 = XYZ_to_CIECAM02(rgb_to_XYZ(rgb), fixed_XYZ, Y_b, L_A, surround=vc)
            spec2 = XYZ_to_CIECAM02(rgb_to_XYZ(r), fixed_XYZ, Y_b, L_A, surround=vc)
            ucs1 = JMh_CIECAM02_to_CAM02UCS([spec1.J, spec1.M, spec1.h])
            ucs2 = JMh_CIECAM02_to_CAM02UCS([spec2.J, spec2.M, spec2.h])
            deltas.append(delta_E_CAM02UCS(ucs1, ucs2))
        if all(d >= min_delta for d in deltas):
            filtered.append((rgb, dE))
        if len(filtered) >= max_candidates:
            break
    return filtered

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + cy + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "9", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class ColourShiftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ColourShift")
        self.base_color = "#950000"
        self.original_surround = "#964301"

        self.min_delta = tk.DoubleVar(value=10.0)
        self.results = []

        self.presets = {
            "Select a preset": (None, None),
            "0": ("#950000", "#964301"),
            "1": ("#8FD16A", "#2DA14E"),
            "2": ("#AE5FAD", "#C892C7"),
            "3": ("#326C36", "#273470"),
        }

        self.top_frame = tk.Frame(root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.preset_selector = ttk.Combobox(self.top_frame, values=list(self.presets.keys()), state="readonly")
        self.preset_selector.current(0)
        self.preset_selector.pack(side=tk.LEFT, padx=5)
        self.preset_selector.bind("<<ComboboxSelected>>", self.apply_preset)

        self.base_display = tk.Canvas(self.top_frame, width=60, height=60, highlightthickness=1, highlightbackground='black')
        self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, width=0)
        self.base_display.bind("<Button-1>", lambda e: self.pick_base_color())
        self.base_display.pack(side=tk.LEFT, padx=5)

        self.surround_display = tk.Canvas(self.top_frame, width=60, height=60, highlightthickness=1, highlightbackground='black')
        self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, width=0)
        self.surround_display.bind("<Button-1>", lambda e: self.pick_surround_color())
        self.surround_display.pack(side=tk.LEFT, padx=5)

        self.solve_btn = tk.Button(self.top_frame, text="Maximal Shift", command=self.solve)
        self.solve_btn.pack(side=tk.LEFT, padx=10)
        ToolTip(self.solve_btn, "Find alternate surround colours that maximally shift the base colour compared to orignal base/surround pair")

        self.base_extreme_btn = tk.Button(self.top_frame, text="Sensitive Bases", command=self.find_shifted_bases)
        self.base_extreme_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.base_extreme_btn, "Find three base colours that are maximally shifted in  current surround")

        self.surround_extreme_btn = tk.Button(self.top_frame, text="Strongest Surrounds", command=self.find_shifted_surrounds)
        self.surround_extreme_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.surround_extreme_btn, "Find three surround colours that maximally influence the appearance of the current base")

        self.save_btn = tk.Button(self.top_frame, text="Save JSON", command=self.save_solution_json)
        self.save_btn.pack(side=tk.LEFT, padx=10)

        self.slider_frame = tk.Frame(root)
        self.slider_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Label(self.slider_frame, text="Min ΔE").pack(side=tk.LEFT, padx=5)
        tk.Scale(self.slider_frame, from_=0.0, to=100.0, orient=tk.HORIZONTAL, resolution=1.0, variable=self.min_delta, length=200).pack(side=tk.LEFT)

        self.preview_frame = tk.Frame(root, bg="#808080")
        self.preview_frame.pack(expand=True, fill=tk.BOTH)

    def apply_preset(self, event):
        preset = self.preset_selector.get()
        base_hex, surround_hex = self.presets[preset]
        if base_hex:
            self.base_color = base_hex
            self.base_display.delete("all")
            self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, width=0)
        if surround_hex:
            self.original_surround = surround_hex
            self.surround_display.delete("all")
            self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, width=0)

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
            box_w = 50
            left_canvas.create_rectangle(0, 0, half_w, h, fill=self.original_surround, width=0)
            left_canvas.create_rectangle(half_w//2 - box_w, h//2 - box_w, half_w//2 + box_w, h//2 + box_w, fill=self.base_color, width=0)

            right_canvas.create_rectangle(0, 0, half_w, h, fill=hex_color, width=0)
            right_canvas.create_rectangle(half_w//2 - box_w, h//2 - box_w, half_w//2 + box_w, h//2 + box_w, fill=self.base_color, width=0)

        def schedule_draw(_event=None):
            comparison_window.after_idle(draw_comparison)

        comparison_window.bind("<Configure>", schedule_draw)
        draw_comparison()

    def solve(self):
        base_rgb = hex_to_rgb(self.base_color)
        surround_rgb = hex_to_rgb(self.original_surround)
        min_delta = self.min_delta.get()
        self.results = compute_appearance_difference(base_rgb, surround_rgb, min_delta=min_delta)

        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        for i, (rgb, dE) in enumerate(self.results):
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
            export_btn = tk.Button(patch_frame, text="Export PNG", command=partial(self.export_comparison_image, hex_col))
            export_btn.pack(pady=2)

    def save_solution_json(self):

            base_rgb = hex_to_rgb(self.base_color)
            surround_rgb = hex_to_rgb(self.original_surround)

            data = {
                "base_color": {
                    "hex": self.base_color,
                    "rgb": base_rgb
                },
                "surround_color": {
                    "hex": self.original_surround,
                    "rgb": surround_rgb
                },
                "candidates": [
                    {
                        "hex": rgb_to_hex(rgb),
                        "rgb": rgb,
                        "deltaE": dE
                    } for rgb, dE in self.results
                ]
            }

            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Save Solution As"
            )
            if filepath:
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=4)

    def export_comparison_image(self, hex_color):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if not file_path:
            return

        size = (300, 150)
        box_size = 20

        img = Image.new("RGB", (size[0], size[1]), "white")
        draw = ImageDraw.Draw(img)

        # Left half with original surround
        draw.rectangle([0, 0, size[0] // 2, size[1]], fill=self.original_surround)
        left_center = (size[0] // 4, size[1] // 2)
        draw.rectangle([
            left_center[0] - box_size, left_center[1] - box_size,
            left_center[0] + box_size, left_center[1] + box_size
        ], fill=self.base_color)

        # Right half with candidate
        draw.rectangle([size[0] // 2, 0, size[0], size[1]], fill=hex_color)
        right_center = (3 * size[0] // 4, size[1] // 2)
        draw.rectangle([
            right_center[0] - box_size, right_center[1] - box_size,
            right_center[0] + box_size, right_center[1] + box_size
        ], fill=self.base_color)

        img.save(file_path)

    def find_shifted_surrounds(self):
        base_rgb = hex_to_rgb(self.base_color)
        candidates = find_extreme_shift_colors(base_rgb, fixed_as_base=True)
        self.show_candidates(candidates, set_surround=True)

    def find_shifted_bases(self):
        surround_rgb = hex_to_rgb(self.original_surround)
        candidates = find_extreme_shift_colors(surround_rgb, fixed_as_base=False)
        self.show_candidates(candidates, set_surround=False)

    def show_candidates(self, candidates, set_surround=True):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        for rgb, dE in candidates:
            hex_col = rgb_to_hex(rgb)
            patch_frame = tk.Frame(self.preview_frame)
            patch_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)

            canvas = tk.Canvas(patch_frame, width=100, height=100, highlightthickness=1, highlightbackground="black")
            canvas.create_rectangle(0, 0, 100, 100, fill=hex_col, width=0)

            if set_surround:
                canvas.bind("<Button-1>", lambda e, c=hex_col: self.set_surround(c))
            else:
                canvas.bind("<Button-1>", lambda e, c=hex_col: self.set_base(c))
            canvas.pack()

            label = tk.Label(patch_frame, text=f"ΔE = {dE:.2f}", bg="white", fg="black")
            label.pack()

    def set_base(self, hex_color):
        self.base_color = hex_color
        self.base_display.delete("all")
        self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, width=0)

    def set_surround(self, hex_color):
        self.original_surround = hex_color
        self.surround_display.delete("all")
        self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, width=0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ColourShiftApp(root)
    root.mainloop()
