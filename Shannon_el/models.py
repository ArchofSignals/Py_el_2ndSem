"""Reusable Shannon-Hartley capacity calculations."""

import math


def snr_db_to_linear(snr_db: float) -> float:
    """Convert SNR from decibels to a linear ratio."""
    return 10 ** (snr_db / 10)


def snr_linear_to_db(snr_linear: float) -> float:
    """Convert a positive linear SNR ratio to decibels."""
    if snr_linear <= 0:
        raise ValueError("Linear SNR must be greater than 0 for dB conversion.")

    return 10 * math.log10(snr_linear)


def calculate_shannon_capacity(bandwidth_hz: float, snr_linear: float) -> float:
    """Calculate Shannon channel capacity in bits per second."""
    if bandwidth_hz <= 0:
        raise ValueError("Bandwidth must be greater than 0.")
    if snr_linear < 0:
        raise ValueError("Linear SNR cannot be negative.")

    return bandwidth_hz * math.log2(1 + snr_linear)


def format_bitrate(bps: float) -> str:
    """Format a bitrate using common units."""
    if bps >= 1e9:
        return f"{bps / 1e9:.2f} Gbps"
    if bps >= 1e6:
        return f"{bps / 1e6:.2f} Mbps"
    if bps >= 1e3:
        return f"{bps / 1e3:.2f} Kbps"
    return f"{bps:.2f} bps"


def calculate_information_transmitted(
    capacity_bps: float, duration_seconds: float
) -> float:
    """Calculate total information transmitted in bits."""
    if duration_seconds < 0:
        raise ValueError("Duration cannot be negative.")

    return capacity_bps * duration_seconds


def calculate_capacity_curve(
    bandwidth_hz: float, min_snr_db: float, max_snr_db: float, step_db: float
) -> tuple[list[float], list[float]]:
    """Generate SNR dB values and matching Shannon capacities."""
    if bandwidth_hz <= 0:
        raise ValueError("Bandwidth must be greater than 0.")
    if step_db <= 0:
        raise ValueError("Step size must be greater than 0.")
    if min_snr_db >= max_snr_db:
        raise ValueError("Minimum SNR must be less than maximum SNR.")

    snr_values = []
    capacities = []
    current = min_snr_db

    while current <= max_snr_db + 1e-9:
        snr_values.append(current)
        capacities.append(
            calculate_shannon_capacity(bandwidth_hz, snr_db_to_linear(current))
        )
        current += step_db

    return snr_values, capacities
