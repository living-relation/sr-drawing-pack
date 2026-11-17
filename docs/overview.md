# Overview

SR Drawing PDF is a Spark Robotic script for Autodesk Fusion. It makes a four-view technical
drawing of the active design and exports it as a PDF.

It is part of the Spark Robotic (SR-) tool set for Fusion. This is a script, not an add-in: you run
it from the Scripts tab, and it does not add a toolbar button that stays loaded.

## Features

- A Save dialog to pick the PDF path (the default name is the design name plus `_drawing`).
- Front, Top, Right and Isometric views on an A3 landscape sheet.
- Overall bounding dimensions, added when Fusion will attach them.
- The temporary drawing is closed without saving. The design stays open.

## Requirements

- Autodesk Fusion (the script was written against Fusion 360 v2703 and later)

## Further reading

- [Install](install.md)
- [Usage](usage.md)
- [Development](development.md)
