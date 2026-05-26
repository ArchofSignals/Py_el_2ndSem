"""Tkinter UI layout and event handling for the Shannon capacity GUI."""

import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np

from models import (
    calculate_ergodic_capacity,
    calculate_information_transmitted,
    calculate_instantaneous_capacities,
    calculate_noise_power,
    calculate_outage_probability,
    calculate_received_snr_db,
    calculate_shannon_capacity,
    free_space_path_loss,
    format_bitrate,
    generate_fading_profile,
    log_distance_path_loss,
    snr_linear_to_db,
    snr_db_to_linear,
)
from plots import CapacityPlot, ChannelSimulatorPlot


UNIT_FACTORS = {
    "Hz": 1,
    "kHz": 1_000,
    "MHz": 1_000_000,
}

FREQUENCY_UNIT_FACTORS = {
    "MHz": 1_000_000,
    "GHz": 1_000_000_000,
}

ENVIRONMENTS = {
    "Free Space": {"exponent": 2.0, "shadowing": 0.0},
    "Rural Flat": {"exponent": 2.2, "shadowing": 2.0},
    "Urban Area": {"exponent": 3.0, "shadowing": 4.0},
    "Dense Urban": {"exponent": 4.5, "shadowing": 6.0},
}

FADING_MODES = ("None/AWGN", "Rayleigh", "Rician")
SIMULATOR_PLOT_MODES = (
    "Capacity vs Distance",
    "Fading vs Time/Samples",
    "Outage Probability",
)


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
        self.channel_tab = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.calculator_tab, text="Calculator")
        self.notebook.add(self.graph_tab, text="AWGN")
        self.notebook.add(self.channel_tab, text="Channel Simulator")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_calculator_tab()
        self._build_graph_tab()
        self._build_channel_tab()

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
        content = self._make_scrollable_tab(self.graph_tab)
        self.graph_bandwidth_var = tk.StringVar(value="1")
        self.graph_bandwidth_unit_var = tk.StringVar(value="MHz")
        self.graph_bandwidth_slider_var = tk.DoubleVar(value=1)
        self.graph_max_snr_slider_var = tk.DoubleVar(value=30)
        self.min_snr_var = tk.StringVar(value="-10")
        self.max_snr_var = tk.StringVar(value="30")
        self.step_snr_var = tk.StringVar(value="1")

        controls = ttk.LabelFrame(content, text="Graph Inputs", padding=12)
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

        plot_frame = ttk.Frame(content, height=380)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        plot_frame.pack_propagate(False)
        self.capacity_plot = CapacityPlot(plot_frame)
        self.capacity_plot.widget.pack(fill=tk.BOTH, expand=True)
        self.update_graph()

    def _build_channel_tab(self):
        content = self._make_scrollable_tab(self.channel_tab)

        self.sim_tx_power_var = tk.StringVar(value="30")
        self.sim_frequency_var = tk.StringVar(value="2.4")
        self.sim_frequency_unit_var = tk.StringVar(value="GHz")
        self.sim_bandwidth_var = tk.StringVar(value="1")
        self.sim_bandwidth_unit_var = tk.StringVar(value="MHz")
        self.sim_distance_var = tk.StringVar(value="100")
        self.sim_distance_slider_var = tk.DoubleVar(value=100)
        self.sim_noise_figure_var = tk.StringVar(value="9")
        self.sim_environment_var = tk.StringVar(value="Free Space")
        self.sim_fading_var = tk.StringVar(value="None/AWGN")
        self.sim_rician_k_var = tk.StringVar(value="6")
        self.sim_plot_mode_var = tk.StringVar(value=SIMULATOR_PLOT_MODES[0])
        self._sim_slider_syncing = False

        self.sim_path_loss_var = tk.StringVar(value="-")
        self.sim_noise_power_var = tk.StringVar(value="-")
        self.sim_snr_var = tk.StringVar(value="-")
        self.sim_capacity_var = tk.StringVar(value="-")

        controls = ttk.LabelFrame(
            content, text="Channel Simulator Inputs", padding=12
        )
        controls.pack(fill=tk.X, pady=(0, 12))

        self._add_labeled_entry(
            controls, "Transmit power (dBm)", self.sim_tx_power_var, 0
        )
        self._add_frequency_entry(
            controls,
            "Carrier frequency",
            self.sim_frequency_var,
            self.sim_frequency_unit_var,
            1,
            command=self.update_channel_simulator,
        )
        self._add_bandwidth_entry(
            controls,
            "Bandwidth",
            self.sim_bandwidth_var,
            self.sim_bandwidth_unit_var,
            2,
            command=self.update_channel_simulator,
        )
        self._add_labeled_entry(controls, "Distance (m)", self.sim_distance_var, 3)
        self._add_scale(
            controls,
            "Distance slider",
            self.sim_distance_slider_var,
            10,
            5000,
            self._on_sim_distance_slider,
            4,
        )
        self._add_labeled_entry(
            controls, "Receiver noise figure (dB)", self.sim_noise_figure_var, 5
        )
        self._add_combobox(
            controls,
            "Environment",
            self.sim_environment_var,
            tuple(ENVIRONMENTS),
            6,
            self.update_channel_simulator,
        )
        self._add_combobox(
            controls,
            "Fading",
            self.sim_fading_var,
            FADING_MODES,
            7,
            self._on_fading_mode_changed,
        )
        self.sim_rician_k_entry = self._add_labeled_entry(
            controls, "Rician K-factor (linear)", self.sim_rician_k_var, 8
        )
        self._add_combobox(
            controls,
            "Plot mode",
            self.sim_plot_mode_var,
            SIMULATOR_PLOT_MODES,
            9,
            self.update_channel_simulator,
        )

        update_button = ttk.Button(
            controls, text="Update Simulation", command=self.update_channel_simulator
        )
        update_button.grid(row=10, column=0, columnspan=2, sticky=tk.EW, pady=(12, 0))
        controls.columnconfigure(1, weight=1)

        results = ttk.LabelFrame(content, text="Link Budget Results", padding=12)
        results.pack(fill=tk.X, pady=(0, 12))
        self._add_result_row(results, "Path loss", self.sim_path_loss_var, 0)
        self._add_result_row(results, "Noise power", self.sim_noise_power_var, 1)
        self._add_result_row(results, "Received SNR", self.sim_snr_var, 2)
        self._add_result_row(results, "Ergodic capacity", self.sim_capacity_var, 3)
        results.columnconfigure(1, weight=1)

        plot_section = ttk.LabelFrame(content, text="Simulation Plot", padding=12)
        plot_section.pack(fill=tk.BOTH, expand=True)
        plot_frame = ttk.Frame(plot_section, height=360)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        plot_frame.pack_propagate(False)
        self.channel_plot = ChannelSimulatorPlot(plot_frame)
        self.channel_plot.widget.pack(fill=tk.BOTH, expand=True)

        self._on_fading_mode_changed()
        self.update_channel_simulator()

    def _make_scrollable_tab(self, tab):
        scroll_canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            tab, orient=tk.VERTICAL, command=scroll_canvas.yview
        )
        content = ttk.Frame(scroll_canvas)
        content.bind(
            "<Configure>",
            lambda _event: scroll_canvas.configure(
                scrollregion=scroll_canvas.bbox("all")
            ),
        )
        content_window = scroll_canvas.create_window((0, 0), window=content, anchor=tk.NW)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.bind(
            "<Configure>",
            lambda event: scroll_canvas.itemconfigure(content_window, width=event.width),
        )
        self._bind_mousewheel(scroll_canvas)
        return content

    def _add_labeled_entry(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(
            row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=6
        )
        return entry

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

    def _add_frequency_entry(
        self, parent, label, variable, unit_variable, row, command=None
    ):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        frequency_frame = ttk.Frame(parent)
        frequency_frame.grid(row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=6)
        frequency_frame.columnconfigure(0, weight=1)

        ttk.Entry(frequency_frame, textvariable=variable).grid(
            row=0, column=0, sticky=tk.EW
        )
        unit_box = ttk.Combobox(
            frequency_frame,
            textvariable=unit_variable,
            values=list(FREQUENCY_UNIT_FACTORS),
            width=5,
            state="readonly",
        )
        unit_box.grid(row=0, column=1, padx=(8, 0))
        if command is not None:
            unit_box.bind("<<ComboboxSelected>>", lambda _event: command())

    def _add_combobox(self, parent, label, variable, values, row, command=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
        )
        combo.grid(row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=6)
        if command is not None:
            combo.bind("<<ComboboxSelected>>", lambda _event: command())
        return combo

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

    def _bind_mousewheel(self, canvas):
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

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

    def update_channel_simulator(self, show_errors=True):
        try:
            inputs = self._read_channel_inputs()
            fading_gains = generate_fading_profile(
                inputs["fading_mode"], 1000, inputs["rician_k_factor"]
            )
            capacities = calculate_instantaneous_capacities(
                inputs["bandwidth_hz"], inputs["snr_db"], fading_gains
            )
            ergodic_capacity = calculate_ergodic_capacity(
                inputs["bandwidth_hz"], inputs["snr_db"], fading_gains
            )

            self.sim_path_loss_var.set(f"{inputs['path_loss_db']:.2f} dB")
            self.sim_noise_power_var.set(f"{inputs['noise_power_dbm']:.2f} dBm")
            self.sim_snr_var.set(f"{inputs['snr_db']:.2f} dB")
            self.sim_capacity_var.set(format_bitrate(ergodic_capacity))
            self._sync_sim_distance_slider(inputs["distance_m"])

            plot_mode = self.sim_plot_mode_var.get()
            if plot_mode == "Capacity vs Distance":
                distances = np.linspace(10, 5000, 180)
                distance_capacities = []
                for distance in distances:
                    path_loss = self._calculate_environment_path_loss(
                        distance,
                        inputs["frequency_hz"],
                        inputs["environment_name"],
                    )
                    snr_db = calculate_received_snr_db(
                        inputs["transmit_power_dbm"],
                        path_loss,
                        inputs["noise_power_dbm"],
                    )
                    distance_capacities.append(
                        calculate_shannon_capacity(
                            inputs["bandwidth_hz"], snr_db_to_linear(snr_db)
                        )
                    )
                self.channel_plot.draw_capacity_distance(
                    distances, distance_capacities, inputs["environment_name"]
                )
            elif plot_mode == "Fading vs Time/Samples":
                self.channel_plot.draw_fading_time(
                    capacities, inputs["fading_mode"], ergodic_capacity
                )
            else:
                max_capacity = max(float(np.max(capacities)), 1)
                thresholds = np.linspace(0, max_capacity * 1.2, 80)
                probabilities = [
                    calculate_outage_probability(capacities, threshold)
                    for threshold in thresholds
                ]
                self.channel_plot.draw_outage_probability(thresholds, probabilities)
        except ValueError as error:
            if show_errors:
                messagebox.showerror("Invalid Simulator Input", str(error))

    def _read_channel_inputs(self):
        bandwidth = self._read_bandwidth(
            self.sim_bandwidth_var, self.sim_bandwidth_unit_var, "Bandwidth"
        )
        frequency = self._read_frequency(
            self.sim_frequency_var, self.sim_frequency_unit_var, "Carrier frequency"
        )
        distance = self._read_float(self.sim_distance_var, "Distance")
        transmit_power = self._read_float(
            self.sim_tx_power_var, "Transmit power"
        )
        noise_figure = self._read_float(
            self.sim_noise_figure_var, "Receiver noise figure"
        )
        rician_k_factor = self._read_float(
            self.sim_rician_k_var, "Rician K-factor"
        )

        if distance <= 0:
            raise ValueError("Distance must be greater than 0.")
        if noise_figure < 0:
            raise ValueError("Receiver noise figure cannot be negative.")

        environment_name = self.sim_environment_var.get()
        path_loss = self._calculate_environment_path_loss(
            distance, frequency, environment_name
        )
        noise_power = calculate_noise_power(bandwidth, noise_figure)
        snr_db = calculate_received_snr_db(transmit_power, path_loss, noise_power)

        return {
            "bandwidth_hz": bandwidth,
            "frequency_hz": frequency,
            "distance_m": distance,
            "transmit_power_dbm": transmit_power,
            "noise_power_dbm": noise_power,
            "path_loss_db": path_loss,
            "snr_db": snr_db,
            "environment_name": environment_name,
            "fading_mode": self.sim_fading_var.get(),
            "rician_k_factor": rician_k_factor,
        }

    def _calculate_environment_path_loss(self, distance_m, frequency_hz, environment):
        if environment == "Free Space":
            return free_space_path_loss(distance_m, frequency_hz)

        config = ENVIRONMENTS[environment]
        return log_distance_path_loss(
            distance_m,
            frequency_hz,
            config["exponent"],
            shadowing_std_db=0,
        )

    def _on_sim_distance_slider(self, value):
        if self._sim_slider_syncing:
            return
        self.sim_distance_var.set(f"{float(value):.1f}")
        self.update_channel_simulator(show_errors=False)

    def _sync_sim_distance_slider(self, distance_m):
        self._sim_slider_syncing = True
        try:
            self.sim_distance_slider_var.set(min(max(distance_m, 10), 5000))
        finally:
            self._sim_slider_syncing = False

    def _on_fading_mode_changed(self):
        if self.sim_fading_var.get() == "Rician":
            self.sim_rician_k_entry.configure(state=tk.NORMAL)
        else:
            self.sim_rician_k_entry.configure(state=tk.DISABLED)
        self.update_channel_simulator(show_errors=False)

    @staticmethod
    def _read_bandwidth(variable, unit_variable, field_name):
        value = ShannonApp._read_float(variable, field_name)
        return value * UNIT_FACTORS[unit_variable.get()]

    @staticmethod
    def _read_frequency(variable, unit_variable, field_name):
        value = ShannonApp._read_float(variable, field_name)
        return value * FREQUENCY_UNIT_FACTORS[unit_variable.get()]

    @staticmethod
    def _read_float(variable, field_name):
        text = variable.get().strip()
        if not text:
            raise ValueError(f"{field_name} is required.")
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a number.") from exc
