"""SR Drawing PDF: a toolbar button that builds a 4-view drawing and exports a PDF.

How it works:
  1. Click SR Drawing PDF. A command dialog asks where to save the PDF.
  2. Click OK. Fusion opens the New Drawing dialog. Click OK (accept the defaults).
  3. The add-in adds Front, Top, Right and Isometric views, adds overall dimensions
     when it can, exports the PDF, and closes the drawing without saving it.
"""
# Compatible with Fusion 360 v2703+
import os
import sys
import time
import traceback

import adsk.core
import adsk.fusion
import adsk.drawing

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from sr_fusion_common import settings, panels  # noqa: E402

CMD_ID = 'srDrawingPdfCmd'
SETTINGS = 'drawing'
_handlers = []  # keep references alive so Python does not garbage-collect them

# Globals to pass state into the drawing-activated handler
_app = None
_ui = None
_design_doc = None
_design = None
_pdf_path = None


def _app_ui():
    return adsk.core.Application.get().userInterface


class _Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            cmd = args.command
            cmd.setDialogInitialSize(440, 180)
            inputs = cmd.commandInputs
            s = settings.load(SETTINGS, {'pdf_path': ''})
            default_name = 'drawing.pdf'
            if app.activeDocument:
                default_name = app.activeDocument.name + '_drawing.pdf'
            path = s.get('pdf_path') or os.path.join(os.path.expanduser('~'), default_name)
            if not path.lower().endswith('.pdf'):
                path += '.pdf'
            inputs.addStringValueInput('pdf_path', 'PDF file', path)
            inputs.addBoolValueInput('browse', 'Choose file...', False, '', False)
            inputs.addTextBoxCommandInput(
                'note', '',
                'After OK, Fusion opens the New Drawing dialog. Click OK there to accept the defaults.',
                2, True)
            for h, ev in ((_Changed(), cmd.inputChanged), (_Execute(), cmd.execute)):
                ev.add(h)
                _handlers.append(h)
            if design is None:
                _app_ui().messageBox('Open a design first.')
        except Exception:
            _app_ui().messageBox('SR Drawing PDF failed to open:\n' + traceback.format_exc())


class _Changed(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            if args.input.id != 'browse':
                return
            inputs = args.inputs
            dlg = _app_ui().createFileDialog()
            dlg.title = 'SR Drawing PDF'
            dlg.filter = 'PDF files (*.pdf)'
            dlg.filterIndex = 0
            cur = inputs.itemById('pdf_path').value
            if cur:
                dlg.initialFilename = os.path.basename(cur)
                folder = os.path.dirname(cur)
                if folder and os.path.isdir(folder):
                    dlg.initialDirectory = folder
            dlg.isMultiSelectEnabled = False
            if dlg.showSave() == adsk.core.DialogResults.DialogOK:
                path = dlg.filename
                if not path.lower().endswith('.pdf'):
                    path += '.pdf'
                inputs.itemById('pdf_path').value = path
            args.input.value = False
        except Exception:
            _app_ui().messageBox(traceback.format_exc())


class _Execute(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            inputs = args.command.commandInputs
            path = (inputs.itemById('pdf_path').value or '').strip()
            if not path:
                _app_ui().messageBox('Pick a PDF file path first.')
                return
            if not path.lower().endswith('.pdf'):
                path += '.pdf'
            settings.save(SETTINGS, {'pdf_path': path})
            start_export(path)
        except Exception:
            _app_ui().messageBox('SR Drawing PDF failed:\n' + traceback.format_exc())


def run(context, pdf_path=None):
    """Register the toolbar button. If pdf_path is passed (smoke tests), export directly."""
    if pdf_path:
        start_export(pdf_path)
        return
    try:
        ui = _app_ui()
        _remove_ui(ui)
        cd = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, 'SR Drawing PDF',
            'Create a four-view drawing of the active design and export a PDF',
            os.path.join(_HERE, 'resources', 'icon'))
        h = _Created()
        cd.commandCreated.add(h)
        _handlers.append(h)
        panels.add_command(ui, cd, CMD_ID)
    except Exception:
        _app_ui().messageBox('SR Drawing PDF run failed:\n' + traceback.format_exc())


def _remove_ui(ui):
    panels.remove_command(ui, CMD_ID)
    cd = ui.commandDefinitions.itemById(CMD_ID)
    if cd:
        cd.deleteMe()


def stop(context):
    try:
        _remove_ui(_app_ui())
        _handlers.clear()
    except Exception:
        pass


def start_export(pdf_path=None):
    global _app, _ui, _design_doc, _design, _pdf_path

    _app = adsk.core.Application.get()
    _ui = _app.userInterface

    try:
        _design_doc = _app.activeDocument
        _design = adsk.fusion.Design.cast(
            _design_doc.products.itemByProductType('DesignProductType')
        )
        if not _design:
            _ui.messageBox('Please open a Fusion 360 design file first.')
            return

        if pdf_path:
            _pdf_path = pdf_path
            if not _pdf_path.lower().endswith('.pdf'):
                _pdf_path += '.pdf'
        else:
            dlg = _ui.createFileDialog()
            dlg.title = 'SR Drawing PDF'
            dlg.filter = 'PDF files (*.pdf)'
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
                'The add-in is ready and listening.\n\n'
                'Please create a new drawing manually via:\n'
                '   File > New Drawing > From Design\n\n'
                'It will automatically add views and export '
                'the PDF as soon as the drawing opens.'
            )

    except Exception:
        _ui.messageBox('Error:\n' + traceback.format_exc())


class DrawingActivatedHandler(adsk.core.DocumentEventHandler):
    """Fires whenever any document becomes active. We check if it is a drawing."""

    def notify(self, args):
        try:
            doc = args.document

            drawing = adsk.drawing.Drawing.cast(
                doc.products.itemByProductType('DrawingProductType')
            )
            if not drawing:
                return

            _app.documentActivated.remove(self)
            # keep other handlers (command created/execute); only drop this listener
            if self in _handlers:
                _handlers.remove(self)

            adsk.doEvents()
            time.sleep(1.5)   # let Fusion finish loading the drawing

            setup_drawing(drawing, doc)

        except Exception:
            _ui.messageBox('Error (event handler):\n' + traceback.format_exc())


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
