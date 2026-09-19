*[Versão em português](README.pt-BR.md)*

# mi-scale-garmin-bridge

Reads the weight from Xiaomi Mi Scale devices over Bluetooth LE — no
need for the official app (Mi Fit / Zepp Life) — and optionally uploads
the result straight to Garmin Connect as a manual weigh-in.

Tested on a **Mi Smart Scale 2**. The protocol used (the standard
Bluetooth SIG "Weight Scale" service, UUID `0x181D`) is shared by
several Xiaomi scales, but the exact byte layout may vary between
models/firmwares — not confirmed on other devices. If it doesn't work
on yours, run with `--raw` and open an issue with the output.

## Why

The scale broadcasts the weight as a BLE advertisement (no pairing
required) while someone is standing on it. That means you can capture
the reading straight from your computer's Bluetooth adapter, without
relying on the manufacturer's app.

## Install

```bash
pip install -r requirements.txt
```

`garminconnect` is only needed if you plan to use `--upload`.

## Find your scale's MAC address

```bash
python mi_scale_reader.py --discover
```

Step on the scale as soon as the command starts — it lists nearby
devices advertising the Weight Scale service.

## Usage

```bash
# just read the weight
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF

# read and upload to Garmin Connect
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --upload

# wait longer (default: 60s)
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --timeout 90

# diagnostic mode: raw dump of every packet received
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --raw
```

To avoid typing `--mac` every time, set the `MI_SCALE_MAC` environment
variable to your scale's address.

## Uploading to Garmin Connect

Uses the [`garminconnect`](https://pypi.org/project/garminconnect/)
library (unofficial). On the first `--upload`, the script asks for your
Garmin email, password, and MFA code (if your account uses one)
interactively in the terminal — nothing is ever saved in plain text.
The authenticated session is cached at `~/.mi_scale_garmin_tokens`,
outside this repository, and reused on future runs.

If you use [Intervals.icu](https://intervals.icu) with your Garmin
account already synced, the weight shows up there automatically — no
second integration needed.

## Windows shortcut

`weigh.bat` runs the upload with a double-click. Edit the file (or set
`MI_SCALE_MAC` as a system environment variable) before using it.

## Protocol (for anyone adapting this to another model)

```
byte0        = control (bit 0x20 = weight stabilized/final)
bytes1-2     = weight, little-endian uint16, unit = raw / 200.0 (kg)
bytes3-9     = the scale's internal RTC timestamp (unused here)
```

Confirmed by comparing decoded values against a real weigh-in: the
reading converges on the same weight in the packets flagged as stable
by the `0x20` bit of the control byte.

## Disclaimer

Unofficial project, not affiliated with Xiaomi or Garmin. Protocol
obtained by reverse-engineering the device's public BLE broadcasts —
use at your own risk.

## License

MIT — see [LICENSE](LICENSE).
