import tkinter as tk
from functools import partial
from threading import Thread
from tkinter import colorchooser, filedialog, ttk

from colourshift.core.algorithms import compute_appearance_difference, find_extreme_shift_colors
from colourshift.core.colour_models import hex_to_rgb, rgb_to_hex
from colourshift.io import save_comparison_image, save_solution_json

from .widgets import ToolTip


class ColourShiftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ColourShift")
        self.base_color = "#950000"
        self.original_surround = "#964301"

        self.min_delta = tk.DoubleVar(value=10.0)
        self.results = []
        self.current_mode = "compare"  # Can be 'compare', 'set_base', 'set_surround'
        self.is_searching = False

        self.presets = {
            "Select a preset": (None, None),
            "0": ("#950000", "#964301"),
            "1": ("#8FD16A", "#2DA14E"),
            "2": ("#AE5FAD", "#C892C7"),
            "3": ("#326C36", "#273470"),
        }

        # Layout containers
        self.top_container = tk.Frame(root)
        self.top_container.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.row_top = tk.Frame(self.top_container)
        self.row_top.pack(fill=tk.X)

        self.preset_selector = ttk.Combobox(
            self.row_top, values=list(self.presets.keys()), state="readonly"
        )
        self.preset_selector.current(0)
        self.preset_selector.pack(side=tk.LEFT, padx=5)
        self.preset_selector.bind("<<ComboboxSelected>>", self.apply_preset)

        self.base_display = tk.Canvas(
            self.row_top, width=60, height=60, highlightthickness=1, highlightbackground="black"
        )
        self.base_display.create_rectangle(0, 0, 60, 60, fill=self.base_color, width=0)
        self.base_display.bind("<Button-1>", lambda e: self.pick_base_color())
        self.base_display.pack(side=tk.LEFT, padx=5)

        self.surround_display = tk.Canvas(
            self.row_top, width=60, height=60, highlightthickness=1, highlightbackground="black"
        )
        self.surround_display.create_rectangle(0, 0, 60, 60, fill=self.original_surround, width=0)
        self.surround_display.bind("<Button-1>", lambda e: self.pick_surround_color())
        self.surround_display.pack(side=tk.LEFT, padx=5)

        self.row_actions = tk.Frame(self.top_container)
        self.row_actions.pack(fill=tk.X, pady=5)

        self.solve_btn = tk.Button(self.row_actions, text="Maximal Shift", command=self.solve)
        self.solve_btn.pack(side=tk.LEFT, padx=10)
        ToolTip(
            self.solve_btn,
            "Find alternate surround colours that maximally shift the base colour "
            "compared to original base/surround pair",
        )

        self.base_extreme_btn = tk.Button(
            self.row_actions, text="Sensitive Bases", command=self.find_shifted_bases
        )
        self.base_extreme_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(
            self.base_extreme_btn,
            "Find three base colours that are maximally shifted in  current surround",
        )

        self.surround_extreme_btn = tk.Button(
            self.row_actions, text="Strongest Surrounds", command=self.find_shifted_surrounds
        )
        self.surround_extreme_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(
            self.surround_extreme_btn,
            "Find three surround colours that maximally influence the appearance "
            "of the current base",
        )

        self.row_save = tk.Frame(self.top_container)
        self.row_save.pack(fill=tk.X, pady=5)

        self.save_btn = tk.Button(self.row_save, text="Save JSON", command=self.save_solution_json)
        self.save_btn.pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(self.row_save, text="", anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.slider_frame = tk.Frame(root)
        self.slider_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Label(self.slider_frame, text="Min ΔE").pack(side=tk.LEFT, padx=5)
        tk.Scale(
            self.slider_frame,
            from_=0.0,
            to=100.0,
            orient=tk.HORIZONTAL,
            resolution=1.0,
            variable=self.min_delta,
            length=200,
        ).pack(side=tk.LEFT)

        self.preview_frame = tk.Frame(root, bg="#808080")
        self.preview_frame.pack(expand=True, fill=tk.BOTH)

        self.preview_label = tk.Label(self.preview_frame, text="", bg="#808080")
        self.preview_label.pack(side=tk.TOP, pady=5)

    def update_preview_label(self):
        if hasattr(self, "preview_label") and self.preview_label.winfo_exists():
            if self.current_mode == "compare":
                self.preview_label.config(
                    text="Click a patch to compare it with the original base/surround pair."
                )
            elif self.current_mode == "set_base":
                self.preview_label.config(text="Click a patch to set base colour.")
            elif self.current_mode == "set_surround":
                self.preview_label.config(text="Click a patch to set surround colour.")

    def draw_swatch(self, canvas, hex_color, size=60):
        canvas.delete("all")
        canvas.create_rectangle(0, 0, size, size, fill=hex_color, width=0)

    def set_base(self, hex_color):
        self.base_color = hex_color
        self.draw_swatch(self.base_display, self.base_color)

    def set_surround(self, hex_color):
        self.original_surround = hex_color
        self.draw_swatch(self.surround_display, self.original_surround)

    def reset_preview(self, mode):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        self.current_mode = mode
        self.preview_label = tk.Label(self.preview_frame, bg="#808080")
        self.preview_label.pack(side=tk.TOP, pady=5)
        self.update_preview_label()

    def create_result_patch(self, rgb, delta, click_handler_factory, include_export=False):
        hex_col = rgb_to_hex(rgb)
        patch_frame = tk.Frame(self.preview_frame)
        patch_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)

        canvas = tk.Canvas(
            patch_frame,
            width=100,
            height=100,
            highlightthickness=1,
            highlightbackground="black",
        )
        self.draw_swatch(canvas, hex_col, size=100)
        canvas.bind("<Button-1>", click_handler_factory(hex_col))
        canvas.pack()

        label = tk.Label(patch_frame, text=f"ΔE = {delta:.2f}", bg="white", fg="black")
        label.pack()

        if include_export:
            export_btn = tk.Button(
                patch_frame,
                text="Export PNG",
                command=partial(self.export_comparison_image, hex_col),
            )
            export_btn.pack(pady=2)

    def set_searching(self, is_searching, message=""):
        self.is_searching = is_searching
        state = tk.DISABLED if is_searching else tk.NORMAL
        for button in (self.solve_btn, self.base_extreme_btn, self.surround_extreme_btn):
            button.config(state=state)
        self.status_label.config(text=message)

    def run_search(self, label, search_fn, render_fn):
        if self.is_searching:
            return

        self.set_searching(True, label)

        def worker():
            try:
                result = search_fn()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: self.finish_search_error(exc))
            else:
                self.root.after(0, lambda: self.finish_search_success(result, render_fn))

        Thread(target=worker, daemon=True).start()

    def finish_search_success(self, result, render_fn):
        self.set_searching(False)
        render_fn(result)

    def finish_search_error(self, exc):
        self.set_searching(False, f"Search failed: {exc}")

    def apply_preset(self, event):
        preset = self.preset_selector.get()
        base_hex, surround_hex = self.presets[preset]
        if base_hex:
            self.set_base(base_hex)
        if surround_hex:
            self.set_surround(surround_hex)

    def pick_base_color(self):
        color = colorchooser.askcolor(title="Pick Base Color")
        if color[1]:
            self.set_base(color[1])

    def pick_surround_color(self):
        color = colorchooser.askcolor(title="Pick Surround Color")
        if color[1]:
            self.set_surround(color[1])

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
            left_canvas.create_rectangle(
                half_w // 2 - box_w,
                h // 2 - box_w,
                half_w // 2 + box_w,
                h // 2 + box_w,
                fill=self.base_color,
                width=0,
            )

            right_canvas.create_rectangle(0, 0, half_w, h, fill=hex_color, width=0)
            right_canvas.create_rectangle(
                half_w // 2 - box_w,
                h // 2 - box_w,
                half_w // 2 + box_w,
                h // 2 + box_w,
                fill=self.base_color,
                width=0,
            )

        def schedule_draw(_event=None):
            comparison_window.after_idle(draw_comparison)

        comparison_window.bind("<Configure>", schedule_draw)
        draw_comparison()

    def solve(self):
        base_rgb = hex_to_rgb(self.base_color)
        surround_rgb = hex_to_rgb(self.original_surround)
        min_delta = self.min_delta.get()

        self.run_search(
            "Searching for maximal shifts...",
            lambda: compute_appearance_difference(base_rgb, surround_rgb, min_delta=min_delta),
            self.show_appearance_results,
        )

    def show_appearance_results(self, results):
        self.results = results
        self.reset_preview("compare")

        for rgb, dE in self.results:
            self.create_result_patch(
                rgb,
                dE,
                click_handler_factory=lambda hex_col: partial(self.handle_patch_click, hex_col),
                include_export=True,
            )

    def save_solution_json(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save Solution As",
        )
        if filepath:
            save_solution_json(filepath, self.base_color, self.original_surround, self.results)

    def export_comparison_image(self, hex_color):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG files", "*.png")]
        )
        if not file_path:
            return

        save_comparison_image(file_path, self.base_color, self.original_surround, hex_color)

    def find_shifted_surrounds(self):
        base_rgb = hex_to_rgb(self.base_color)
        self.run_search(
            "Searching for strongest surrounds...",
            lambda: find_extreme_shift_colors(base_rgb, fixed_as_base=True),
            lambda candidates: self.show_candidates(candidates, set_surround=True),
        )

    def find_shifted_bases(self):
        surround_rgb = hex_to_rgb(self.original_surround)
        self.run_search(
            "Searching for sensitive bases...",
            lambda: find_extreme_shift_colors(surround_rgb, fixed_as_base=False),
            lambda candidates: self.show_candidates(candidates, set_surround=False),
        )

    def show_candidates(self, candidates, set_surround=True):
        mode = "set_surround" if set_surround else "set_base"
        self.reset_preview(mode)

        def click_handler_factory(hex_col):
            if set_surround:
                return lambda _event: self.set_surround(hex_col)
            return lambda _event: self.set_base(hex_col)

        for rgb, dE in candidates:
            self.create_result_patch(rgb, dE, click_handler_factory=click_handler_factory)


def main():
    root = tk.Tk()
    root.app = ColourShiftApp(root)
    root.mainloop()
