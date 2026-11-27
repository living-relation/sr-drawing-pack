"""Fusion button: read the design in short steps, then leave Fusion.

Each step is its own Fusion event, so one step returns before the next starts.
Nothing here sleeps or polls. The sheet is built by generate_sheet.py in
another process, which also opens the editor.
"""
import os
import tempfile
import traceback

CMD_ID = 'srSheetJobCmd'
SHEET_EVENT = 'srDrawingSheetStep'

_handlers = []
_event = None
_pending = None


def install(ui):
    """Add the SR Sheet button and the one-step event. Safe to call again."""
    import adsk.core
    global _event
    app = adsk.core.Application.get()
    if _event is None:
        _event = app.registerCustomEvent(SHEET_EVENT)
        handler = _Step()
        _event.add(handler)
        _handlers.append(handler)
    old = ui.commandDefinitions.itemById(CMD_ID)
    if old:
        old.deleteMe()
    cmd = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, 'SR Sheet',
        'Read the open design in short steps, then build the sheet outside Fusion',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'icon'))
    created = _Created()
    cmd.commandCreated.add(created)
    _handlers.append(created)
    from sr_fusion_common import panels
    panels.add_command(ui, cmd, CMD_ID)


def stop(ui):
    """Remove the button and the event."""
    import adsk.core
    global _event, _pending
    from sr_fusion_common import panels
    panels.remove_command(ui, CMD_ID)
    cmd = ui.commandDefinitions.itemById(CMD_ID)
    if cmd:
        cmd.deleteMe()
    _pending = None
    if _event is not None:
        try:
            adsk.core.Application.get().unregisterCustomEvent(SHEET_EVENT)
        except Exception:
            pass
        _event = None
    _handlers.clear()


def begin(out_dir=None):
    """Start a read. The first event runs the list step. Returns the folder."""
    out_dir = out_dir or tempfile.mkdtemp(prefix='sr-drawing-')
    from sheet_job import fresh_state
    _queue(fresh_state(), out_dir)
    return out_dir


def _queue(state, out_dir):
    """Ask Fusion to run one step. Returns immediately."""
    import adsk.core
    global _pending
    _pending = (state, out_dir)
    adsk.core.Application.get().fireCustomEvent(SHEET_EVENT, '')


class _Created(object):
    """Filled in as a Fusion handler by install, once adsk is present."""


class _Step(object):
    """Filled in as a Fusion handler by install."""


def _bind_handlers():
    """Replace the placeholders with Fusion handler classes. Called from install."""
    import adsk.core

    class Created(adsk.core.CommandCreatedEventHandler):
        def notify(self, args):
            try:
                cmd = args.command
                cmd.commandInputs.addTextBoxCommandInput(
                    'note', '',
                    'Reads the open design in short steps, builds the sheet in the background, and opens the editor.',
                    2, True)
                handler = Execute()
                cmd.execute.add(handler)
                _handlers.append(handler)
            except Exception:
                _message('SR Sheet failed to open:\n' + traceback.format_exc())

    class Execute(adsk.core.CommandEventHandler):
        def notify(self, args):
            try:
                begin()
            except Exception:
                _message('SR Sheet failed:\n' + traceback.format_exc())

    class Step(adsk.core.CustomEventHandler):
        def notify(self, args):
            global _pending
            if not _pending:
                return
            state, out_dir = _pending
            _pending = None
            try:
                import fusion_read
                from sheet_job import one_step, spawn_background
                state, _result = one_step(state, out_dir, fusion_read)
                if state['phase'] == 'ready':
                    spawn_background(out_dir)
                    return
                _queue(state, out_dir)
            except Exception:
                _message('SR Sheet read failed:\n' + traceback.format_exc())

    return Created, Step


def _message(text):
    import adsk.core
    adsk.core.Application.get().userInterface.messageBox(text, 'SR Sheet')


# Real handler classes, created when this module is used inside Fusion.
try:
    import adsk.core  # noqa: F401
    _Created, _Step = _bind_handlers()
except Exception:
    pass
