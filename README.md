# SR Drawing PDF

A Spark Robotic Fusion script that makes a four-view technical drawing of the active design and
exports it as a PDF.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- Run the script to open a Save dialog and pick where the PDF should go.
- Fusion then opens the **New Drawing** dialog. Click OK (accept the defaults).
- The script adds Front, Top, Right and Isometric views on an A3 landscape sheet, adds overall dimensions when it can, exports the PDF, and closes the drawing without saving it. The design stays open.
- Dimensions are best-effort; if Fusion will not attach them, the PDF is still exported.

## Requirements

- Autodesk Fusion

## Install

1. Clone this repo and keep the folder on disk.
2. In Fusion: **Utilities > Add-ins > Scripts and Add-ins > Scripts tab > + (green plus)** next to My Scripts, and pick the `SRDrawingPDF` folder inside the clone.

   Or copy or link the `SRDrawingPDF` folder into `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\` and restart Fusion.
3. The script is listed as **SR Drawing PDF**. Run it from Scripts and Add-ins (or press S and search for it).

See [docs/install.md](docs/install.md) for the full steps, including uninstall.

## Usage

Open a design, run **SR Drawing PDF**, pick the PDF path, then click OK on the New Drawing dialog. See [docs/usage.md](docs/usage.md).

## Documentation

- [Overview](docs/overview.md)
- [Install](docs/install.md)
- [Usage](docs/usage.md)
- [Development](docs/development.md)
- [Documentation index](docs/README.md)

## Development

```
python tools/check.py
```

CI runs the same check. `dev/fusion_smoke.py` is a live test that runs inside Fusion. A full PDF export still needs the New Drawing confirmation click. See [docs/development.md](docs/development.md).

## Contributing

Work on a branch and open a pull request against `main`. Update `docs/` when behavior changes. See [docs/development.md](docs/development.md) and [AGENTS.md](AGENTS.md).

## License

This project is licensed under the [MIT License](LICENSE). Copyright (c) 2026 Spark Robotic.
