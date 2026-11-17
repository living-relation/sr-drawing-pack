"""SR Drawing PDF: create a front/top/right/isometric drawing of the active design and export a PDF.

How it works:
  1. Run the script. A Save dialog appears; pick where to save the PDF.
  2. Fusion opens the New Drawing dialog. Click OK (accept the defaults).
  3. The script adds Front, Top, Right and Isometric views, adds overall dimensions when it can,
     exports the PDF, and closes the drawing without saving it.
"""
# Compatible with Fusion 360 v2703+
import adsk.core
import adsk.fusion
import adsk.drawing
import traceback
import time

# Globals to pass state into the event handler
_app        = None
_ui         = None
_design_doc = None
_design     = None
_pdf_path   = None
_handlers   = []   # keep references alive so Python doesn't garbage-collect them


def run(context, pdf_path=None):
    global _app, _ui, _design_doc, _design, _pdf_path

    _app = adsk.core.Application.get()
    _ui  = _app.userInterface

    try:
        # Verify a design is active
        _design_doc = _app.activeDocument
        _design = adsk.fusion.Design.cast(
            _design_doc.products.itemByProductType('DesignProductType')
        )
        if not _design:
            _ui.messageBox('Please open a Fusion 360 design file first.')
            return

        # Ask where to save the PDF (or use a path passed by a smoke test)
        if pdf_path:
            _pdf_path = pdf_path
            if not _pdf_path.lower().endswith('.pdf'):
                _pdf_path += '.pdf'
        else:
            dlg = _ui.createFileDialog()
            dlg.title        = 'SR Drawing PDF'
            dlg.filter       = 'PDF files (*.pdf)'
            dlg.initialFilename = _design_doc.name + '_drawing'
            dlg.isMultiSelectEnabled = False
            if dlg.showSave() != adsk.core.DialogResults.DialogOK:
                return
            _pdf_path = dlg.filename
            if not _pdf_path.lower().endswith('.pdf'):
                _pdf_path += '.pdf'

        # Register a documentActivated listener -- fires when the new drawing opens
        handler = DrawingActivatedHandler()
        _handlers.append(handler)
        _app.documentActivated.add(handler)

        # Trigger the New Drawing dialog (user just clicks OK)
        triggered = False
        for cmd_id in ['FusionDrawingCreateFromComponentsCommand',
                        'NewDrawingMenuCommand',
                        'NewFusionDrawingDocumentCommand']:
            cmdDef = _ui.commandDefinitions.itemById(cmd_id)
            if cmdDef:
                cmdDef.execute()
                triggered = True
                break

        if not triggered:
            _ui.messageBox(
                'Script is ready and listening.\n\n'
                'Please create a new drawing manually via:\n'
                '   File > New Drawing > From Design\n\n'
                'The script will automatically add views and export '
                'the PDF as soon as the drawing opens.'
            )

    except Exception:
        _ui.messageBox(f'Error:\n{traceback.format_exc()}')


class DrawingActivatedHandler(adsk.core.DocumentEventHandler):
    """Fires whenever any document becomes active. We check if it is a drawing."""

    def notify(self, args):
        try:
            doc = args.document

            # Only care about drawing documents
            drawing = adsk.drawing.Drawing.cast(
                doc.products.itemByProductType('DrawingProductType')
            )
            if not drawing:
                return

            # Unregister ourselves so we don't fire again
            _app.documentActivated.remove(self)
            _handlers.clear()

            adsk.doEvents()
            time.sleep(1.5)   # let Fusion finish loading the drawing

            setup_drawing(drawing, doc)

        except Exception:
            _ui.messageBox(f'Error (event handler):\n{traceback.format_exc()}')


def setup_drawing(drawing, draw_doc):
    """Add views, dimensions, and export PDF."""
    try:
        sheet = drawing.sheets.item(0)

        # A3 landscape
        fmt = sheet.sheetFormat
        fmt.sheetSize   = adsk.drawing.DrawingSheetSizes.A3SheetSize
        fmt.isLandscape = True
        sheet.sheetFormat = fmt
        adsk.doEvents()

        # ── Base view: Front (lower-left) ────────────────────────────────────
        bi = sheet.drawingViews.createBaseViewInput()
        bi.referencedDocument = _design_doc
        bi.position      = adsk.core.Point3D.create(10.5, 7.4, 0)   # cm
        bi.scale         = 0                                           # auto
        bi.viewOrientation = adsk.drawing.DrawingViewOrientations.FrontDrawingViewOrientation
        bi.viewStyle     = adsk.drawing.DrawingViewStyles.VisibleAndHiddenEdgesDrawingViewStyle
        front = sheet.drawingViews.addBaseView(bi)
        adsk.doEvents()
        time.sleep(0.5)

        # ── Projected views ───────────────────────────────────────────────────
        def proj(parent, x, y):
            pi = sheet.drawingViews.createProjectedViewInput(parent)
            pi.position = adsk.core.Point3D.create(x, y, 0)
            v = sheet.drawingViews.addProjectedView(pi)
            adsk.doEvents()
            return v

        # Layout:  Top (above Front) | Iso (top-right)
        #          Front (lower-left)| Right (lower-right)
        top   = proj(front, 10.5, 19.0)
        right = proj(front, 24.0,  7.4)
        iso   = proj(front, 31.5, 19.0)

        try:
            iso.orientation = adsk.drawing.DrawingViewOrientations.HomeDrawingViewOrientation
        except Exception:
            pass

        adsk.doEvents()
        time.sleep(0.5)

        # ── Overall bounding dimensions ───────────────────────────────────────
        try:
            add_dimensions(sheet, front, top, _design)
        except Exception:
            pass   # dimensions are best-effort

        # ── Export PDF ────────────────────────────────────────────────────────
        exp  = drawing.exportManager
        opts = exp.createPDFExportOptions()
        opts.filename          = _pdf_path
        opts.isOpenAfterExport = True
        exp.execute(opts)
        adsk.doEvents()

        _ui.messageBox(f'SR Drawing PDF saved to:\n{_pdf_path}')

        draw_doc.close(False)   # close drawing, keep design open

    except Exception:
        _ui.messageBox(f'Error (setup_drawing):\n{traceback.format_exc()}')


def add_dimensions(sheet, front_view, top_view, design):
    """Add width, height, and depth overall dimensions."""
    bb = design.rootComponent.boundingBox
    if not bb:
        return

    # Fusion units are cm
    w = bb.maxPoint.x - bb.minPoint.x   # width
    h = bb.maxPoint.z - bb.minPoint.z   # height
    d = bb.maxPoint.y - bb.minPoint.y   # depth

    dims = sheet.drawingDimensions

    def pt(x, y):
        return adsk.core.Point3D.create(x, y, 0)

    def linear(view, p1, p2, text_pt):
        try:
            di = dims.createLinearDimensionInput(
                adsk.drawing.DimensionReferenceGeometryTypes.PointDimensionReferenceGeometryType,
                adsk.drawing.DimensionReferenceGeometryTypes.PointDimensionReferenceGeometryType,
            )
            di.setByPoints(view, p1, view, p2, text_pt)
            dims.addLinearDimension(di)
        except Exception:
            pass

    # Front: width across the bottom, height up the right side
    fp = front_view.position
    linear(front_view,
           pt(fp.x - w/2, fp.y - h/2), pt(fp.x + w/2, fp.y - h/2),
           pt(fp.x,        fp.y - h/2 - 1.5))
    linear(front_view,
           pt(fp.x + w/2, fp.y - h/2), pt(fp.x + w/2, fp.y + h/2),
           pt(fp.x + w/2 + 1.5, fp.y))

    # Top: depth up the right side
    tp = top_view.position
    linear(top_view,
           pt(tp.x + w/2, tp.y - d/2), pt(tp.x + w/2, tp.y + d/2),
           pt(tp.x + w/2 + 1.5, tp.y))