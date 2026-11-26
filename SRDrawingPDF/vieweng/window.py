"""Depth window. Windows uses the graphics card. OSMesa is a fallback."""
import os
import sys


def offscreen_backend(platform=None, force=None, has_display=None):
    """Which depth window to open.

    Windows uses the graphics card (WGL). OSMesa is only an explicit request,
    or the Linux fallback when there is no display. Selecting OSMesa on
    Windows when osmesa.dll is missing crashes, so it is never the default there.
    """
    plat = sys.platform if platform is None else platform
    choice = os.environ.get('SRDP_GL') if force is None else force
    if choice:
        choice = str(choice).strip().lower()
    if choice in ('osmesa', 'mesa', 'cpu'):
        return 'osmesa'
    if choice in ('native', 'gpu', 'wgl'):
        return 'native'
    if plat == 'win32':
        return 'native'
    if has_display is None:
        has_display = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
    if str(plat).startswith('linux') and not has_display:
        return 'osmesa'
    return 'native'


def _offscreen_window():
    """A depth window that does not need a screen."""
    import vtk
    backend = offscreen_backend()
    if backend == 'osmesa':
        if not hasattr(vtk, 'vtkOSOpenGLRenderWindow'):
            raise RuntimeError(
                'OSMesa was requested for the depth picture, but this VTK build has no OSMesa window.')
        win = vtk.vtkOSOpenGLRenderWindow()
    else:
        win = vtk.vtkRenderWindow()
    try:
        win.SetOffScreenRendering(1)
    except Exception as exc:
        raise RuntimeError('the depth window could not be created: %s' % exc)
    return win


def _draw_depth(win):
    """Draw one depth tile. A failure is an error with a clear message."""
    try:
        win.Render()
    except Exception as exc:
        raise RuntimeError(
            'the depth picture could not be drawn (%s). '
            'On Windows the graphics card window is used; set SRDP_GL=osmesa only when OSMesa is installed.'
            % exc)
