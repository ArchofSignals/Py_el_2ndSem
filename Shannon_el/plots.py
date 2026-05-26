"""Matplotlib helpers for the Shannon capacity GUI."""

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from models import calculate_capacity_curve, format_bitrate


class CapacityPlot:
    """Embedded capacity-versus-SNR plot."""

    def __init__(self, parent):
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.widget = self.canvas.get_tk_widget()
        self.hover_annotation = None
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)

    def draw(
        self,
        bandwidth_hz: float,
        min_snr_db: float,
        max_snr_db: float,
        step_db: float,
        operating_point: tuple[float, float, float] | None = None,
    ):
        snr_values, capacities = calculate_capacity_curve(
            bandwidth_hz, min_snr_db, max_snr_db, step_db
        )
        capacity_mbps = [value / 1e6 for value in capacities]

        self.axes.clear()
        self.axes.plot(
            snr_values,
            capacity_mbps,
            color="#1f77b4",
            linewidth=2,
            label="Graph bandwidth curve",
        )

        if operating_point is not None:
            snr_db, capacity_bps, marker_bandwidth_hz = operating_point
            self.axes.scatter(
                [snr_db],
                [capacity_bps / 1e6],
                color="#d62728",
                marker="x",
                s=90,
                linewidths=2.5,
                label=(
                    "Current operating point "
                    f"({format_bitrate(marker_bandwidth_hz).replace('bps', 'Hz')})"
                ),
                zorder=5,
            )

        self.axes.set_title(
            f"Capacity vs SNR for Bandwidth {format_bitrate(bandwidth_hz).replace('bps', 'Hz')}"
        )
        self.axes.set_xlabel("SNR (dB)")
        self.axes.set_ylabel("Capacity (Mbps)")
        self.axes.grid(True, linestyle="--", alpha=0.45)
        self.axes.legend(loc="best")
        self.hover_annotation = self.axes.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox={"boxstyle": "round", "fc": "white", "ec": "#666666", "alpha": 0.9},
            arrowprops={"arrowstyle": "->", "color": "#666666"},
        )
        self.hover_annotation.set_visible(False)
        self.figure.tight_layout()
        self.canvas.draw()

    def _on_motion(self, event):
        if self.hover_annotation is None:
            return

        if event.inaxes != self.axes or event.xdata is None or event.ydata is None:
            if self.hover_annotation.get_visible():
                self.hover_annotation.set_visible(False)
                self.canvas.draw_idle()
            return

        self.hover_annotation.xy = (event.xdata, event.ydata)
        self.hover_annotation.set_text(
            f"SNR: {event.xdata:.2f} dB\nCapacity: {event.ydata:.2f} Mbps"
        )
        self.hover_annotation.set_visible(True)
        self.canvas.draw_idle()


class ChannelSimulatorPlot:
    """Embedded plots for link-budget and fading simulations."""

    def __init__(self, parent):
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.widget = self.canvas.get_tk_widget()

    def draw_capacity_distance(self, distances_m, capacities_bps, environment_name):
        capacities_mbps = np.maximum(np.asarray(capacities_bps) / 1e6, 0)

        self.axes.clear()
        self.axes.semilogx(
            distances_m,
            capacities_mbps,
            color="#287c71",
            linewidth=2,
        )
        self.axes.set_title(f"Capacity vs Distance ({environment_name})")
        self.axes.set_xlabel("Distance (m, log scale)")
        self.axes.set_ylabel("Capacity (Mbps)")
        self.axes.set_xlim(float(np.min(distances_m)), float(np.max(distances_m)))
        self.axes.set_ylim(bottom=0)
        self.axes.grid(True, linestyle="--", alpha=0.45)
        self.axes.grid(True, which="minor", linestyle=":", alpha=0.22)
        self.figure.tight_layout()
        self.canvas.draw()

    def draw_fading_time(self, capacities_bps, fading_name, average_capacity_bps):
        samples = np.arange(1, len(capacities_bps) + 1)

        self.axes.clear()
        self.axes.plot(
            samples,
            np.asarray(capacities_bps) / 1e6,
            color="#7b3f98",
            linewidth=1.4,
            label="Instantaneous capacity",
        )
        self.axes.axhline(
            average_capacity_bps / 1e6,
            color="#d16f2f",
            linestyle="--",
            linewidth=1.8,
            label="Average capacity",
        )
        self.axes.set_title(f"Time-Domain Fading Capacity ({fading_name})")
        self.axes.set_xlabel("Sample")
        self.axes.set_ylabel("Capacity (Mbps)")
        self.axes.grid(True, linestyle="--", alpha=0.45)
        self.axes.legend(loc="best")
        self.figure.tight_layout()
        self.canvas.draw()

    def draw_outage_probability(self, thresholds_bps, probabilities):
        probabilities = np.clip(np.asarray(probabilities), 0, 1)

        self.axes.clear()
        self.axes.plot(
            np.asarray(thresholds_bps) / 1e6,
            probabilities,
            color="#b13f53",
            linewidth=2,
            drawstyle="steps-post",
        )
        self.axes.set_title("Outage Probability")
        self.axes.set_xlabel("Capacity threshold (Mbps)")
        self.axes.set_ylabel("P(capacity below threshold)")
        self.axes.set_xlim(left=0)
        self.axes.set_ylim(-0.02, 1.02)
        self.axes.grid(True, linestyle="--", alpha=0.45)
        self.figure.tight_layout()
        self.canvas.draw()
