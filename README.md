# Instrument Tapstrap Test

Read raw motion data from a **Tap Strap 2** over Bluetooth: the five per-finger
accelerometers (~200 Hz) and the thumb IMU (gyro + accelerometer, ~208 Hz).

## One-time setup

1. **Update firmware** in the Tap Manager app (raw mode needs firmware ≥ 2.3.27).
2. **Turn on Developer Mode** in Tap Manager. Without it the raw stream may not start.
3. **Pair the strap** in your computer's Bluetooth settings.
4. Install (Python 3.10+):

   ```bash
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Run it

```bash
python stream_raw.py                  # live per-finger readout in the terminal
python stream_raw.py --csv take1      # also log take1_fingers.csv and take1_imu.csv
python live_plot.py                   # scrolling plot: finger |accel| + thumb gyro
python stream_raw.py --demo           # synthetic data, to test without the strap
```

Ctrl+C (or closing the plot) puts the strap back into normal text mode and disconnects.

Useful flags (both scripts): `--finger-range {2,4,8,16}` g, `--gyro-range {125,250,500,1000,2000}` dps,
`--imu-range {2,4,8,16}` g, `--address <BLE id>` if you have more than one Tap.
Pick a smaller range for more resolution on gentle motion, a larger one if hard taps clip.

## Using it in your own code

```python
import asyncio
from tapstrap import TapRawStream, SensorConfig, FingerAccelSample

async def main():
    async with TapRawStream(SensorConfig(finger_accel_g=8)) as tap:
        async for s in tap.samples():
            if isinstance(s, FingerAccelSample):
                print(s.device_ms, s.index)          # (x, y, z) in g
            else:                                    # ImuSample
                print(s.device_ms, s.gyro_dps, s.accel_g)

asyncio.run(main())
```

Or register a callback with `tap.on_sample(fn)`, where `fn(sample, host_time_s)` is called for
every sample. That's the lower-latency path for driving sound.

## What the data is

| Stream | Fields | Units | Rate |
|---|---|---|---|
| `FingerAccelSample` | `thumb`, `index`, `middle`, `ring`, `pinky`, each `(x, y, z)` | g | ~200 Hz |
| `ImuSample` (thumb) | `gyro_dps (x, y, z)`, `accel_g (x, y, z)` | deg/s, g | ~208 Hz |

- `device_ms` is the strap's own millisecond clock (not wall time). CSVs also record host time.
- At rest each accelerometer reads ≈1 g total because of gravity. A tap is a short spike in |a|.
- Axis directions are defined relative to the hardware. See the diagram in Tap's
  [raw sensors docs](https://github.com/TapWithUs/tap-python-sdk/blob/main/docs/v1/explanation/raw-sensors.md).
- Ranges can't be changed while streaming. Restart the script to change them.

## How it works

`tapstrap/stream.py` uses Tap's official [tap-python-sdk](https://github.com/TapWithUs/tap-python-sdk)
to connect and to send the raw-mode command. The SDK re-sends it every 10 s, which the firmware
requires or it drops back to text mode. The bytes from the Nordic UART TX characteristic
(`6e400003-…`) are decoded in `tapstrap/decode.py`. Each message is a 32-bit little-endian header
(top bit: 1 = finger accels, 0 = IMU; low 31 bits = timestamp ms), followed by 15 or 6 int16 values.
Those values are scaled per Tap's [Raw Sensors Mode spec](https://tapwithus.atlassian.net/wiki/spaces/TD/pages/792002574/Tap+Strap+Raw+Sensors+Mode).

Run the decoder tests with `pytest`.
