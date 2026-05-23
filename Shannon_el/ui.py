"""Tkinter UI layout and event handling for the Shannon capacity GUI."""

import tkinter as tk
from tkinter import messagebox, ttk

from models import (
    calculate_information_transmitted,
    calculate_shannon_capacity,
    format_bitrate,
    snr_linear_to_db,
    snr_db_to_linear,
)
from plots import CapacityPlot


UNIT_FACTORS = {
    "Hz": 1,
    "kHz": 1_000,
    "MHz": 1_000_000,
}


class ShannonApp(ttk.Frame):
    """Main notebook-based application frame."""

    def __init__(self, master):
        super().__init__(master, padding=12)
        self.pack(fill=tk.BOTH, expand=True)
        self.current_operating_point = None
        self._graph_slider_syncing = False

        self.notebook = ttk.Notebook(self)
        self.calculator_tab = ttk.Frame(self.notebook, padding=12)
        self.graph_tab = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.calculator_tab, text="Calculator")
        self.notebook.add(self.graph_tab, text="Graph")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_calculator_tab()
        self._build_graph_tab()

    def _build_calculator_tab(self):
        self.bandwidth_var = tk.StringVar(value="1")
        self.bandwidth_unit_var = tk.StringVar(value="MHz")
        self.snr_mode_var = tk.StringVar(value="dB")
        self.snr_value_var = tk.StringVar(value="10")
        self.duration_var = tk.StringVar()

        self.raw_capacity_var = tk.StringVar(value="-")
        self.formatted_capacity_var = tk.StringVar(value="-")
        self.info_transmitted_var = tk.StringVar(value="-")

        input_frame = ttk.LabelFrame(self.calculator_tab, text="Inputs", padding=12)
        output_frame = ttk.LabelFrame(self.calculator_tab, text="Results", padding=12)
        input_frame.pack(fill=tk.X, pady=(0, 12))
        output_frame.pack(fill=tk.X)

        self._add_bandwidth_entry(
            input_frame, "Bandwidth", self.bandwidth_var, self.bandwidth_unit_var, 0
        )

        ttk.Label(input_frame, text="SNR mode").grid(row=1, column=0, sticky=tk.W, pady=6)
        mode_frame = ttk.Frame(input_frame)
        mode_frame.grid(row=1, column=1, sticky=tk.W, pady=6)
        ttk.Radiobutton(
            mode_frame, text="dB", variable=self.snr_mode_var, value="dB"
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(
            mode_frame, text="Linear", variable=self.snr_mode_var, value="linear"
        ).pack(side=tk.LEFT)

        self._add_labeled_entry(input_frame, "SNR value", self.snr_value_var, 2)
        self._add_labeled_entry(
            input_frame, "Duration (seconds, optional)", self.duration_var, 3
        )

        calculate_button = ttk.Button(
            input_frame, text="Calculate", command=self.calculate_capacity
        )
        calculate_button.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(12, 0))

        input_frame.columnconfigure(1, weight=1)

        self._add_result_row(output_frame, "Raw capacity", self.raw_capacity_var, 0)
        self._add_result_row(
            output_frame, "Formatted capacity", self.formatted_capacity_var, 1
        )
        self._add_result_row(
            output_frame, "Information transmitted", self.info_transmitted_var, 2
        )
        output_frame.columnconfigure(1, weight=1)

    def _build_graph_tab(self):
        self.graph_bandwidth_var = tk.StringVar(value="1")
        self.graph_bandwidth_unit_var = tk.StringVar(value="MHz")
        self.graph_bandwidth_slider_var = tk.DoubleVar(value=1)
        self.graph_max_snr_slider_var = tk.DoubleVar(value=30)
        self.min_snr_var = tk.StringVar(value="-10")
        self.max_snr_var = tk.StringVar(value="30")
        self.step_snr_var = tk.StringVar(value="1")

        controls = ttk.LabelFrame(self.graph_tab, text="Graph Inputs", padding=12)
        controls.pack(fill=tk.X, pady=(0, 12))

        self._add_bandwidth_entry(
            controls,
            "Bandwidth",
            self.graph_bandwidth_var,
            self.graph_bandwidth_unit_var,
            0,
            command=self.update_graph,
        )
        self._add_scale(
            controls,
            "Bandwidth slider",
            self.graph_bandwidth_slider_var,
            0.1,
            100,
            self._on_graph_bandwidth_slider,
            1,
        )
        self._add_labeled_entry(controls, "Minimum SNR (dB)", self.min_snr_var, 2)
        self._add_labeled_entry(controls, "Maximum SNR (dB)", self.max_snr_var, 3)
        self._add_scale(
            controls,
            "Maximum SNR slider",
            self.graph_max_snr_slider_var,
            -20,
            60,
            self._on_graph_max_snr_slider,
            4,
        )
        self._add_labeled_entry(controls, "Step size (dB)", self.step_snr_var, 5)

        update_button = ttk.Button(controls, text="Update Graph", command=self.update_graph)
        update_button.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=(12, 0))
        controls.columnconfigure(1, weight=1)

        plot_frame = ttk.Frame(self.graph_tab)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        self.capacity_plot = CapacityPlot(plot_frame)
        self.capacity_plot.widget.pack(fill=tk.BOTH, expand=True)
        self.update_graph()

    def _add_labeled_entry(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=6
        )

    def _add_bandwidth_entry(
        self, parent, label, variable, unit_variable, row, command=None
    ):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        bandwidth_frame = ttk.Frame(parent)
        bandwidth_frame.grid(row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=6)
        bandwidth_frame.columnconfigure(0, weight=1)

        ttk.Entry(bandwidth_frame, textvariable=variable).grid(
            row=0, column=0, sticky=tk.EW
        )
        unit_box = ttk.Combobox(
            bandwidth_frame,
            textvariable=unit_variable,
            values=list(UNIT_FACTORS),
            width=5,
            state="readonly",
        )
        unit_box.grid(row=0, column=1, padx=(8, 0))
        if command is not None:
            unit_box.bind("<<ComboboxSelected>>", lambda _event: command())

    def _add_scale(self, parent, label, variable, from_value, to_value, command, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        ttk.Scale(
            parent,
            variable=variable,
            from_=from_value,
            to=to_value,
            command=command,
        ).grid(row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=6)

    def _add_result_row(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        ttk.Label(parent, textvariable=variable).grid(
            row=row, column=1, sticky=tk.W, padx=(12, 0), pady=6
        )

    def calculate_capacity(self):
        try:
            bandwidth = self._read_bandwidth(
                self.bandwidth_var, self.bandwidth_unit_var, "Bandwidth"
            )
            snr_value = self._read_float(self.snr_value_var, "SNR value")

            if bandwidth <= 0:
                raise ValueError("Bandwidth must be greater than 0.")

            if self.snr_mode_var.get() == "dB":
                snr_linear = snr_db_to_linear(snr_value)
                snr_db = snr_value
            else:
                if snr_value < 0:
                    raise ValueError("Linear SNR cannot be negative.")
                snr_linear = snr_value
                snr_db = snr_linear_to_db(snr_value) if snr_value > 0 else None

            capacity = calculate_shannon_capacity(bandwidth, snr_linear)
            self.raw_capacity_var.set(f"{capacity:,.2f} bits per second")
            self.formatted_capacity_var.set(format_bitrate(capacity))
            self.current_operating_point = (
                (snr_db, capacity, bandwidth) if snr_db is not None else None
            )

            duration_text = self.duration_var.get().strip()
            if duration_text:
                duration = float(duration_text)
                transmitted = calculate_information_transmitted(capacity, duration)
                self.info_transmitted_var.set(f"{transmitted:,.2f} bits")
            else:
                self.info_transmitted_var.set("-")

            self.update_graph(show_errors=False)

        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error))

    def update_graph(self, show_errors=True):
        try:
            bandwidth = self._read_bandwidth(
                self.graph_bandwidth_var,
                self.graph_bandwidth_unit_var,
                "Bandwidth",
            )
            min_snr = self._read_float(self.min_snr_var, "Minimum SNR")
            max_snr = self._read_float(self.max_snr_var, "Maximum SNR")
            step = self._read_float(self.step_snr_var, "Step size")
            self._sync_graph_sliders()
            self.capacity_plot.draw(
                bandwidth, min_snr, max_snr, step, self.current_operating_point
            )
        except ValueError as error:
            if show_errors:
                messagebox.showerror("Invalid Graph Input", str(error))

    def _on_graph_bandwidth_slider(self, value):
        if self._graph_slider_syncing:
            return
        self.graph_bandwidth_var.set(f"{float(value):.2f}")
        self.update_graph(show_errors=False)

    def _on_graph_max_snr_slider(self, value):
        if self._graph_slider_syncing:
            return
        self.max_snr_var.set(f"{float(value):.1f}")
        self.update_graph(show_errors=False)

    def _sync_graph_sliders(self):
        self._graph_slider_syncing = True
        try:
            bandwidth_value = self._read_float(
                self.graph_bandwidth_var, "Bandwidth"
            )
            max_snr = self._read_float(self.max_snr_var, "Maximum SNR")
            self.graph_bandwidth_slider_var.set(
                min(max(bandwidth_value, 0.1), 100)
            )
            self.graph_max_snr_slider_var.set(min(max(max_snr, -20), 60))
        finally:
            self._graph_slider_syncing = False

    @staticmethod
    def _read_bandwidth(variable, unit_variable, field_name):
        value = ShannonApp._read_float(variable, field_name)
        return value * UNIT_FACTORS[unit_variable.get()]

    @staticmethod
    def _read_float(variable, field_name):
        text = variable.get().strip()
        if not text:
            raise ValueError(f"{field_name} is required.")
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a number.") from exc
