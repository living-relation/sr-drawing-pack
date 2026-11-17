# Install

## Requirements

- Autodesk Fusion
- This repository, cloned or downloaded to a folder you can keep on disk

## Add the script in Fusion

1. Open Autodesk Fusion.
2. Open **Utilities > Add-ins > Scripts and Add-ins** (Shift+S in current builds).
3. Open the **Scripts** tab.
4. Click the green **+** next to **My Scripts** and pick the `SRDrawingPDF` folder inside your clone. That folder contains `SRDrawingPDF.py`, `SRDrawingPDF.manifest`, and `ScriptIcon.svg`. Do not pick the repository root.
5. The script is listed as **SR Drawing PDF**. Select it and click **Run** when you want to use it.

Alternatively, copy or link the `SRDrawingPDF` folder into `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\` and restart Fusion. A directory junction works well: updating the clone is enough; the next Run picks up the new files.

If Fusion does not list the script, confirm you pointed at `SRDrawingPDF`, not the repo root.

## Uninstall

In the same Scripts and Add-Ins dialog, remove **SR Drawing PDF** from My Scripts if Fusion provides that option. You can also delete a junction or copy under the Scripts folder.

## Next

See [Usage](usage.md) after the script is installed.
