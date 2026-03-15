# LoRa Coverage Planner

> Forked from [meshtastic/meshtastic-site-planner](https://github.com/meshtastic/meshtastic-site-planner). This is a modified version — see commit history for changes.

## About

A web-based tool for predicting LoRa radio coverage. It creates radio coverage maps using the ITM/Longley-Rice model and SPLAT! software by John A. Magliacane, KD2BD (https://www.qsl.net/kd2bd/splat.html). The maps are used for planning tower deployments and for estimating the coverage provided by a LoRa mesh network. Model parameters are adjustable for different frequencies, transmit powers, and hardware configurations.

The terrain elevation tiles are streamed from AWS Open Data (https://registry.opendata.aws/terrain-tiles/), which are based on the NASA SRTM (Shuttle Radar Topography) dataset (https://www.earthdata.nasa.gov/data/instruments/srtm).

## Usage

The minimal steps for creating a coverage prediction are:

1. Run a local or deployed copy and open the tool in a web browser.
2. In `Site Parameters > Site / Transmitter`, enter a name for the site, the geographic coordinates, and the antenna height above ground. Select your hardware preset or manually input the transmit power, frequency, and antenna gain for your device.
3. In `Site Parameters > Receiver`, enter the receiver sensitivity, the receiver height, and the receiver antenna gain.
4. In `Site Parameters > Simulation`, enter the maximum range for the simulation in kilometers. Selecting long ranges (> 50 km) will result in longer computation times.
5. Press "Run Simulation." The coverage map will be displayed when the calculation completes.

Multiple tower sites can be added to the simulation by repeating these steps.

## Model and Assumptions

This tool runs a physics simulation that depends on several assumptions. The most important ones are:

1. The SRTM terrain model is accurate to 90 meters.
2. There are no obstructions besides terrain that attenuate radio signals. These include trees, artificial structures such as buildings, or transient effects like precipitation.
3. Antennas are isotropic in the horizontal plane (we do not account for directional antennas).
4. Reflections from the upper atmosphere (skywave propagation) are negligible. This is less accurate when the signal frequency is low (less than approximately 50 MHz).

A detailed description of the model parameters and their recommended values is available in [parameters.md](parameters.md).

## Building

Requirements:

- Podman
- Git
- pnpm

```bash
git clone --recurse-submodules <repo-url> && cd lora-planner

pnpm i && pnpm run build

podman build -f Containerfile -t lora-planner .
podman run -p 8080:8080 -v lora-data:/data lora-planner
```

For running a development server, use `pnpm run dev`.

## License

This project is licensed under the GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.
