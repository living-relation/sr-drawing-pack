"""Fusion's own drawing views.

Outside Fusion this engine is not available and says so. Inside Fusion it
asks the drawing API for the view curves. It does not sleep, poll, or take
a lock. The old Fusion desktop lock is retired and is not used here.
"""


class FusionEngine(object):
    name = 'fusion'
    label = 'Fusion drawing'

    def available(self):
        try:
            import adsk.core  # noqa: F401
            import adsk.drawing  # noqa: F401
            app = adsk.core.Application.get()
        except Exception:
            return False, 'the Fusion engine only runs inside Fusion (adsk.drawing is not here)'
        if app is None or app.activeDocument is None:
            return False, 'the Fusion engine needs an open design'
        return True, ''

    def project_view(self, name, parts=None, step=None, **opts):
        ok, why = self.available()
        if not ok:
            raise RuntimeError(why)
        return _fusion_view(name)


def _fusion_view(name):
    """Read one named view's curves from an open Fusion drawing.

    This does not create a drawing, does not wait for one, and does not call
    the add-in's run() or stop(). There is no desktop lock.
    """
    import adsk.core
    app = adsk.core.Application.get()
    drawing = None
    try:
        docs = app.documents
        for i in range(docs.count):
            item = docs.item(i)
            try:
                prods = item.products
                for j in range(prods.count):
                    prod = prods.item(j)
                    if getattr(prod, 'productType', '') == 'DrawingProductType':
                        drawing = prod
                        break
            except Exception:
                continue
            if drawing is not None:
                break
    except Exception as exc:
        raise RuntimeError('Fusion is open but its drawing views could not be read: %s' % exc)
    if drawing is None:
        raise RuntimeError(
            'Fusion is open but there is no drawing to read curves from. '
            'The Fusion engine does not create one and does not wait.')
    raise RuntimeError(
        'Fusion drawing "%s" is open, but reading its %s view curves is not wired yet'
        % (getattr(drawing, 'name', 'drawing'), name))
