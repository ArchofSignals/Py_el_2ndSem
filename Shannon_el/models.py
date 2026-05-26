"""Reusable Shannon-Hartley capacity calculations."""

import math

import numpy as np


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


def calculate_noise_power(bandwidth_hz: float, noise_figure_db: float = 9) -> float:
    """Calculate thermal noise power in dBm for a receiver bandwidth."""
    if bandwidth_hz <= 0:
        raise ValueError("Bandwidth must be greater than 0.")

    return -174 + 10 * math.log10(bandwidth_hz) + noise_figure_db


def free_space_path_loss(distance_m: float, frequency_hz: float) -> float:
    """Calculate free-space path loss in dB."""
    if distance_m <= 0:
        raise ValueError("Distance must be greater than 0.")
    if frequency_hz <= 0:
        raise ValueError("Frequency must be greater than 0.")

    return 20 * math.log10(distance_m) + 20 * math.log10(frequency_hz) - 147.55


def log_distance_path_loss(
    distance_m: float,
    frequency_hz: float,
    path_loss_exponent: float,
    shadowing_std_db: float = 0,
    reference_distance_m: float = 1,
    rng=None,
) -> float:
    """Calculate log-distance path loss in dB with optional shadowing."""
    if path_loss_exponent <= 0:
        raise ValueError("Path loss exponent must be greater than 0.")
    if shadowing_std_db < 0:
        raise ValueError("Shadowing standard deviation cannot be negative.")
    if reference_distance_m <= 0:
        raise ValueError("Reference distance must be greater than 0.")

    effective_distance = max(distance_m, reference_distance_m)
    base_loss = free_space_path_loss(reference_distance_m, frequency_hz)
    shadowing = 0
    if shadowing_std_db > 0:
        generator = rng if rng is not None else np.random.default_rng()
        shadowing = float(generator.normal(0, shadowing_std_db))

    return (
        base_loss
        + 10 * path_loss_exponent * math.log10(effective_distance / reference_distance_m)
        + shadowing
    )


def calculate_received_snr_db(
    transmit_power_dbm: float,
    path_loss_db: float,
    noise_power_dbm: float,
    tx_gain_dbi: float = 0,
    rx_gain_dbi: float = 0,
) -> float:
    """Calculate received SNR from a simple link budget."""
    received_power_dbm = transmit_power_dbm + tx_gain_dbi + rx_gain_dbi - path_loss_db
    return received_power_dbm - noise_power_dbm


def generate_fading_profile(
    profile_type: str,
    num_samples: int,
    rician_k_factor: float = 6,
    rng=None,
) -> np.ndarray:
    """Generate normalized complex channel coefficients."""
    if num_samples <= 0:
        raise ValueError("Number of samples must be greater than 0.")
    if rician_k_factor < 0:
        raise ValueError("Rician K-factor cannot be negative.")

    normalized_type = profile_type.strip().lower()
    generator = rng if rng is not None else np.random.default_rng()

    if normalized_type in {"none", "awgn", "none/awgn"}:
        return np.ones(num_samples, dtype=complex)

    scatter = (
        generator.normal(0, 1, num_samples)
        + 1j * generator.normal(0, 1, num_samples)
    ) / math.sqrt(2)

    if normalized_type == "rayleigh":
        return scatter

    if normalized_type == "rician":
        dominant = math.sqrt(rician_k_factor / (rician_k_factor + 1))
        diffuse = math.sqrt(1 / (rician_k_factor + 1)) * scatter
        return dominant + diffuse

    raise ValueError("Fading profile must be None/AWGN, Rayleigh, or Rician.")


def calculate_ergodic_capacity(
    bandwidth_hz: float, base_snr_db: float, fading_gains
) -> float:
    """Calculate average Shannon capacity over fading channel samples."""
    if bandwidth_hz <= 0:
        raise ValueError("Bandwidth must be greater than 0.")

    gains = np.asarray(fading_gains)
    instantaneous_snr = snr_db_to_linear(base_snr_db) * np.abs(gains) ** 2
    capacities = bandwidth_hz * np.log2(1 + instantaneous_snr)
    return float(np.mean(capacities))


def calculate_instantaneous_capacities(
    bandwidth_hz: float, base_snr_db: float, fading_gains
) -> np.ndarray:
    """Calculate instantaneous capacity samples for fading channel gains."""
    if bandwidth_hz <= 0:
        raise ValueError("Bandwidth must be greater than 0.")

    gains = np.asarray(fading_gains)
    instantaneous_snr = snr_db_to_linear(base_snr_db) * np.abs(gains) ** 2
    return bandwidth_hz * np.log2(1 + instantaneous_snr)


def calculate_outage_probability(capacities_bps, threshold_bps: float) -> float:
    """Calculate probability that capacity falls below a target threshold."""
    if threshold_bps < 0:
        raise ValueError("Outage threshold cannot be negative.")

    capacities = np.asarray(capacities_bps)
    if capacities.size == 0:
        raise ValueError("At least one capacity sample is required.")

    return float(np.mean(capacities < threshold_bps))
