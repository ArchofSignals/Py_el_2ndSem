# Shannon Capacity GUI

Tkinter application for calculating Shannon-Hartley channel capacity and plotting capacity versus SNR.

## Features

- Calculator tab for bandwidth, SNR, and optional transmission duration.
- Graph tab for plotting capacity over an SNR dB range.
- Red operating-point marker from the latest calculator result.
- Hover tooltip for reading SNR and capacity values from the graph.
- Unit dropdowns for bandwidth values in Hz, kHz, or MHz.
- Live graph sliders for bandwidth and maximum SNR.
- Reusable calculation helpers in `models.py`.
- Matplotlib embedded directly inside the tkinter window.

## Requirements

- Python 3
- tkinter
- matplotlib

The current environment already includes tkinter and matplotlib. If matplotlib is missing on another system, install it with:

```powershell
pip install -r requirements.txt
```

## Run

From the assignment folder:

```powershell
python Shannon_el/shannon_el.py
```

## Example Check

For bandwidth `1` MHz and SNR `10` dB, the calculator should show about `3.46 Mbps`.
