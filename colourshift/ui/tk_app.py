import tkinter as tk
from dataclasses import replace
from functools import partial
from threading import Thread
from tkinter import colorchooser, filedialog, ttk

from colourshift.core.algorithms import (
    EMPIRICAL_MODEL_LABEL,
    MODE_MAXIMAL_SURROUND_SHIFT,
    MODE_SENSITIVE_BASES,
    MODE_STRONGEST_SURROUNDS,
    OBJECTIVE_CHROMATIC,
    OBJECTIVE_TOTAL,
    find_empirical_maximal_surround_shift,
    find_empirical_sensitive_bases,
    find_empirical_strongest_surrounds,
)
from colourshift.core.colour_models import hex_to_rgb, rgb_to_hex
from colourshift.core.config import DEFAULT_CONFIG
from colourshift.io import save_comparison_image, save_search_result_json

from .widgets import ToolTip

OBJECTIVE_TOTAL_LABEL = "Total appearance shift"
OBJECTIVE_CHROMATIC_LABEL = "Chromatic shift"
OBJECTIVE_BY_LABEL = {
    OBJECTIVE_TOTAL_LABEL: OBJECTIVE_TOTAL,
    OBJECTIVE_CHROMATIC_LABEL: OBJECTIVE_CHROMATIC,
}


class ColourShiftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ColourShift")
        self.base_color = "#950000"
        self.original_surround = "#964301"
        self.min_delta = tk.DoubleVar(value=10.0)
        self.objective_mode = tk.StringVar(value=OBJECTIVE_CHROMATIC_LABEL)
        self.current_result = None
        self.current_mode = None
        self.is_searching = False
        self.search_generation = 0
        self.presets = {
            "Select a preset": (None, None),
            "0": ("#950000", "#964301"),
            "1": ("#8FD16A", "#2DA14E"),
            "2": ("#AE5FAD", "#C892C7"),
            "3": ("#326C36", "#273470"),
        }

        top = tk.Frame(root)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        row_top = tk.Frame(top)
        row_top.pack(fill=tk.X)

        self.preset_selector = ttk.Combobox(row_top, values=list(self.presets), state="readonly")
        self.preset_selector.current(0)
        self.preset_selector.pack(side=tk.LEFT, padx=5)
        self.preset_selector.bind("<<ComboboxSelected>>", self.apply_preset)

        self.base_display = self._colour_canvas(row_top, self.base_color, self.pick_base_color)
        self.surround_display = self._colour_canvas(
            row_top, self.original_surround, self.pick_surround_color
        )

        row_actions = tk.Frame(top)
        row_actions.pack(fill=tk.X, pady=5)
        self.solve_btn = tk.Button(row_actions, text="Maximal Shift", command=self.solve)
        self.solve_btn.pack(side=tk.LEFT, padx=10)
        ToolTip(self.solve_btn, "Find surrounds that shift this base from the initial pairing.")
        self.base_extreme_btn = tk.Button(
            row_actions, text="Sensitive Bases", command=self.find_shifted_bases
        )
        self.base_extreme_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.base_extreme_btn, "Find bases most shifted by the current surround.")
        self.surround_extreme_btn = tk.Button(
            row_actions, text="Strongest Surrounds", command=self.find_shifted_surrounds
        )
        self.surround_extreme_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.surround_extreme_btn, "Find surrounds that most shift the current base.")

        row_options = tk.Frame(top)
        row_options.pack(fill=tk.X, pady=5)
        tk.Label(row_options, text=EMPIRICAL_MODEL_LABEL).pack(side=tk.LEFT, padx=(10, 12))
        tk.Label(row_options, text="Objective").pack(side=tk.LEFT, padx=(0, 2))
        self.objective_selector = ttk.Combobox(
            row_options,
            textvariable=self.objective_mode,
            values=(OBJECTIVE_TOTAL_LABEL, OBJECTIVE_CHROMATIC_LABEL),
            state="readonly",
            width=22,
        )
        self.objective_selector.pack(side=tk.LEFT, padx=2)
        self.objective_selector.bind("<<ComboboxSelected>>", self.invalidate_result)
        self.save_btn = tk.Button(
            row_options, text="Save JSON", command=self.save_result_json, state=tk.DISABLED
        )
        self.save_btn.pack(side=tk.LEFT, padx=(12, 4))
        self.status_label = tk.Label(row_options, text="", anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=10)

        slider_frame = tk.Frame(root)
        slider_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        tk.Label(slider_frame, text="Min result separation").pack(side=tk.LEFT, padx=5)
        self.min_delta_scale = tk.Scale(
            slider_frame,
            from_=0.0,
            to=20.0,
            orient=tk.HORIZONTAL,
            resolution=0.25,
            variable=self.min_delta,
            length=200,
            command=self.invalidate_result,
        )
        self.min_delta_scale.pack(side=tk.LEFT)

        self.preview_frame = tk.Frame(root, bg="#808080")
        self.preview_frame.pack(expand=True, fill=tk.BOTH)
        self.reset_preview()

    def _colour_canvas(self, parent, colour, callback):
        canvas = tk.Canvas(
            parent, width=60, height=60, highlightthickness=1, highlightbackground="black"
        )
        self.draw_swatch(canvas, colour)
        canvas.bind("<Button-1>", lambda _event: callback())
        canvas.pack(side=tk.LEFT, padx=5)
        return canvas

    @staticmethod
    def draw_swatch(canvas, hex_color, size=60):
        canvas.delete("all")
        canvas.create_rectangle(0, 0, size, size, fill=hex_color, width=0)

    def invalidate_result(self, _event=None):
        self.current_result = None
        self.current_mode = None
        if hasattr(self, "save_btn"):
            self.save_btn.config(state=tk.DISABLED)
        if hasattr(self, "preview_frame") and not self.is_searching:
            self.reset_preview()

    def set_base(self, hex_color):
        self.base_color = hex_color
        self.draw_swatch(self.base_display, hex_color)
        self.invalidate_result()

    def set_surround(self, hex_color):
        self.original_surround = hex_color
        self.draw_swatch(self.surround_display, hex_color)
        self.invalidate_result()

    def reset_preview(self, instruction="Run a search to inspect candidate colours."):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        tk.Label(self.preview_frame, text=instruction, bg="#808080").pack(side=tk.TOP, pady=5)

    def set_searching(self, active, message=""):
        self.is_searching = active
        button_state = tk.DISABLED if active else tk.NORMAL
        for button in (self.solve_btn, self.base_extreme_btn, self.surround_extreme_btn):
            button.config(state=button_state)
        self.preset_selector.config(state="disabled" if active else "readonly")
        self.objective_selector.config(state="disabled" if active else "readonly")
        self.min_delta_scale.config(state=button_state)
        self.base_display.config(state="disabled" if active else "normal")
        self.surround_display.config(state="disabled" if active else "normal")
        self.save_btn.config(
            state=tk.NORMAL if not active and self.current_result is not None else tk.DISABLED
        )
        self.status_label.config(text=message)

    def run_search(self, label, search_fn):
        if self.is_searching:
            return
        self.invalidate_result()
        self.search_generation += 1
        generation = self.search_generation
        self.set_searching(True, label)

        def worker():
            try:
                result = search_fn()
            except Exception as exc:
                self.root.after(
                    0, lambda captured_exc=exc: self.finish_search_error(generation, captured_exc)
                )
            else:
                self.root.after(0, lambda: self.finish_search_success(generation, result))

        Thread(target=worker, daemon=True).start()

    def finish_search_success(self, generation, result):
        if generation != self.search_generation:
            return
        self.current_result = result
        self.current_mode = result.mode
        self.set_searching(False)
        self.show_result(result)

    def finish_search_error(self, generation, exc):
        if generation != self.search_generation:
            return
        self.set_searching(False, f"Search failed: {exc}")

    def _config(self):
        return replace(
            DEFAULT_CONFIG,
            adapting_luminance=64.0,
            min_delta=self.min_delta.get(),
        )

    def _objective(self):
        return OBJECTIVE_BY_LABEL[self.objective_mode.get()]

    def solve(self):
        base, surround = hex_to_rgb(self.base_color), hex_to_rgb(self.original_surround)
        config, objective = self._config(), self._objective()
        self.run_search(
            "Searching for maximal shifts...",
            lambda: find_empirical_maximal_surround_shift(
                base, surround, config=config, objective=objective
            ),
        )

    def find_shifted_surrounds(self):
        base, config, objective = hex_to_rgb(self.base_color), self._config(), self._objective()
        self.run_search(
            "Searching for strongest surrounds...",
            lambda: find_empirical_strongest_surrounds(base, config=config, objective=objective),
        )

    def find_shifted_bases(self):
        surround = hex_to_rgb(self.original_surround)
        config, objective = self._config(), self._objective()
        self.run_search(
            "Searching for sensitive bases...",
            lambda: find_empirical_sensitive_bases(surround, config=config, objective=objective),
        )

    def show_result(self, result):
        if not result.candidates:
            self.reset_preview(
                "No finite candidates were returned for these inputs. "
                "Try another pairing or a smaller minimum separation."
            )
            return
        instructions = {
            MODE_MAXIMAL_SURROUND_SHIFT: "Click a patch to compare it with the initial pairing.",
            MODE_STRONGEST_SURROUNDS: "Click a patch to use it as the surround.",
            MODE_SENSITIVE_BASES: "Click a patch to use it as the base.",
        }
        self.reset_preview(instructions[result.mode])
        group = tk.LabelFrame(
            self.preview_frame,
            text=f"{EMPIRICAL_MODEL_LABEL} — ranked by {result.objective} shift",
            bg="#808080",
            fg="white",
        )
        group.pack(side=tk.TOP, fill=tk.X, expand=True, padx=8, pady=5)
        for candidate in result.candidates:
            self.create_result_patch(group, result, candidate)

    def create_result_patch(self, parent, result, candidate):
        hex_col = rgb_to_hex(candidate.rgb)
        frame = tk.Frame(parent)
        frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        canvas = tk.Canvas(frame, width=100, height=100, highlightthickness=1)
        self.draw_swatch(canvas, hex_col, size=100)
        if result.mode == MODE_MAXIMAL_SURROUND_SHIFT:
            canvas.bind("<Button-1>", partial(self.handle_patch_click, hex_col))
        elif result.mode == MODE_STRONGEST_SURROUNDS:
            canvas.bind("<Button-1>", lambda _event: self.set_surround(hex_col))
        else:
            canvas.bind("<Button-1>", lambda _event: self.set_base(hex_col))
        canvas.pack()
        tk.Label(
            frame,
            text=(
                f"{hex_col}\nTotal = {candidate.total_shift:.2f}"
                f"\nChromatic = {candidate.chromatic_shift:.2f}"
            ),
            bg="white",
        ).pack()
        if result.mode == MODE_MAXIMAL_SURROUND_SHIFT:
            tk.Button(
                frame, text="Export PNG", command=partial(self.export_comparison_image, hex_col)
            ).pack(pady=2)

    def apply_preset(self, _event=None):
        base, surround = self.presets[self.preset_selector.get()]
        if base:
            self.base_color = base
            self.draw_swatch(self.base_display, base)
        if surround:
            self.original_surround = surround
            self.draw_swatch(self.surround_display, surround)
        self.invalidate_result()

    def pick_base_color(self):
        colour = colorchooser.askcolor(title="Pick Base Color")[1]
        if colour:
            self.set_base(colour)

    def pick_surround_color(self):
        colour = colorchooser.askcolor(title="Pick Surround Color")[1]
        if colour:
            self.set_surround(colour)

    def _maximal_colours(self, candidate_hex):
        result = self.current_result
        if result is None or result.mode != MODE_MAXIMAL_SURROUND_SHIFT:
            raise ValueError("No maximal-shift result is available")
        return rgb_to_hex(result.base_rgb), rgb_to_hex(result.surround_rgb), candidate_hex

    def handle_patch_click(self, hex_color, _event=None):
        base_hex, surround_hex, candidate_hex = self._maximal_colours(hex_color)
        window = tk.Toplevel(self.root)
        window.title("Perceptual Shift Comparison")
        left = tk.Canvas(window, highlightthickness=0)
        right = tk.Canvas(window, highlightthickness=0)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def draw(_event=None):
            window.update_idletasks()
            width, height = max(window.winfo_width() // 2, 1), window.winfo_height()
            for canvas, surround in ((left, surround_hex), (right, candidate_hex)):
                canvas.delete("all")
                canvas.create_rectangle(0, 0, width, height, fill=surround, width=0)
                canvas.create_rectangle(
                    width // 2 - 50,
                    height // 2 - 50,
                    width // 2 + 50,
                    height // 2 + 50,
                    fill=base_hex,
                    width=0,
                )

        window.bind("<Configure>", lambda _event: window.after_idle(draw))
        draw()

    def save_result_json(self):
        if self.current_result is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON files", "*.json")]
        )
        if path:
            save_search_result_json(path, self.current_result)

    def export_comparison_image(self, candidate_hex):
        if self.current_result is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG files", "*.png")]
        )
        if path:
            base, surround, candidate = self._maximal_colours(candidate_hex)
            save_comparison_image(path, base, surround, base, candidate)


def main():
    root = tk.Tk()
    root.app = ColourShiftApp(root)
    root.mainloop()
