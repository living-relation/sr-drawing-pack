# Usage

## Before you start

1. Install the script as described in [Install](install.md).
2. Open the Fusion design you want to draw.

## Run

1. In **Scripts and Add-ins**, select **SR Drawing PDF** and click **Run** (or press S and search for it).
2. A Save dialog appears. Pick where to save the PDF. The default file name is the design name plus `_drawing`.
3. Fusion opens the **New Drawing** dialog. Click OK and accept the defaults. The script is listening for that drawing to open.
4. The script sets the sheet to A3 landscape, adds Front, Top, Right and Isometric views, tries to add overall dimensions, exports the PDF, and closes the drawing without saving it.

If no design is open, the script asks you to open one first. If it cannot trigger the New Drawing command, it tells you to create a drawing yourself with **File > New Drawing > From Design**; it will still finish the views and PDF when that drawing opens.

## Results

A message box reports the PDF path when the export finishes. The design document stays open. The temporary drawing is discarded.

## Limits and known issues

- You must click OK on the New Drawing dialog. That confirmation cannot be skipped.
- Dimensions are best-effort. If Fusion will not attach them, the PDF is still exported.
- View layout is fixed for an A3 landscape sheet. Very large or very small models may need a manual scale change; the script uses automatic scale for the base view.
