"""The depth window must not pick OSMesa on Windows."""
import sys

from vieweng.window import _draw_depth, _offscreen_window, offscreen_backend


def test_windows_uses_the_graphics_card_not_osmesa():
    assert offscreen_backend('win32', force='', has_display=False) == 'native'
    assert offscreen_backend('win32', force='osmesa', has_display=False) == 'osmesa'
    assert offscreen_backend('linux', force='', has_display=False) == 'osmesa'
    assert offscreen_backend('linux', force='', has_display=True) == 'native'
    assert offscreen_backend('linux', force='native', has_display=False) == 'native'


def test_the_depth_window_can_draw_a_tiny_picture():
    import vtk
    win = _offscreen_window()
    if sys.platform == 'win32':
        assert 'OSMesa' not in win.GetClassName()
    ren = vtk.vtkRenderer()
    win.AddRenderer(ren)
    cube = vtk.vtkCubeSource()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(cube.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    ren.AddActor(actor)
    ren.ResetCamera()
    win.SetSize(32, 32)
    _draw_depth(win)
    values = vtk.vtkFloatArray()
    win.GetZbufferData(0, 0, 31, 31, values)
    assert values.GetNumberOfTuples() == 32 * 32
