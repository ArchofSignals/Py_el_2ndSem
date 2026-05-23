"""Matplotlib helpers for the Shannon capacity GUI."""

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
