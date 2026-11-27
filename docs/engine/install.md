# Install

## Requirements

- Autodesk Fusion
- This repository, cloned or downloaded to a folder you can keep on disk

## Add the add-in in Fusion

The intended install is a directory junction from Fusion's AddIns folder to the `SRDrawingPDF` folder inside this clone, not a copy. A copied folder will not follow `git pull`. Open a normal Command Prompt (not Run as administrator). `mklink /J` does not need elevation. Both paths below are absolute, so no `cd` is required. Run:

```
mklink /J "%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SRDrawingPDF" "<path-to-this-clone>\SRDrawingPDF"
```

Replace `<path-to-this-clone>` with this repo's clone path on that PC. The active-folder path differs per PC.

Then open Autodesk Fusion, press **Shift+S**, open the **Add-Ins** tab, select **SR Drawing PDF**, tick **Run on Startup**, and click **Run**. After a later `git pull`, restart the add-in (**Stop**, then **Run**) or restart Fusion. An automatic updater (coming soon, in the workstation repo) will pull updates hourly and notify you to restart Fusion.

If Fusion does not list the add-in, confirm you pointed at `SRDrawingPDF`, not the repo root.


The **SR Drawing PDF** button is added to several Design-workspace panels, not only the Manage or Add-Ins tab:

- Utilities / Add-Ins (`SolidScriptsAddinsPanel`)
- Make (`SolidMakePanel`)
- Insert (`InsertPanel`)
- A custom **SR Tools** tab and panel (created if needed)

By default the button is pinned on **SR Tools** and on Add-Ins. The other panels still get the command; Fusion keeps your own pin or unpin choice after the first run.

To change the list, edit `%APPDATA%/SRDrawingPDF/panels.json`:

```json
{
  "panel_ids": [
    "SolidScriptsAddinsPanel",
    "SolidMakePanel",
    "InsertPanel",
    "SRToolsPanel"
  ]
}
```

Unknown panel ids are skipped. Restart the add-in (Stop, then Run, or restart Fusion) after you change the file. Stopping the add-in removes every toolbar control for this command, including leftovers from an older panel list. If the SR Tools panel and tab are empty after that, they are removed too.

## Uninstall

In the same Scripts and Add-Ins dialog, select **SR Drawing PDF**, click **Stop**, then remove it from the list if Fusion provides that option. You can also delete the junction under the AddIns folder. Settings in `%APPDATA%\SRDrawingPDF\` are left in place unless you delete them yourself.

## Next

See [Usage](usage.md) after the add-in is installed.
