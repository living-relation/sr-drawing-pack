"""The PDF draws a title-block logo, PNG or SVG, instead of an empty frame."""
import base64
import struct
import zlib

from sheet2d.canvas import Sheet
from sheet2d.commands import execute
from sheet2d.formats import attach_template, default_template, set_logo
from sheet2d.model import DrawingDocument
from sheet2d.pdf import write_pdf
from sheet2d.render import render_sheets

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="32">'
    '<rect width="80" height="32" fill="#1c1c1c"/>'
    '<text x="40" y="21" text-anchor="middle" font-size="14" fill="#ffffff">SR</text>'
    '</svg>'
)


def _png(width, height, rgb, alpha=None):
    if alpha is None:
        raw = b''
        stride = width * 3
        for y in range(height):
            raw += b'\x00' + rgb[y * stride:(y + 1) * stride]
        color = 2
    else:
        raw = b''
        for y in range(height):
            raw += b'\x00'
            for x in range(width):
                i = y * width + x
                raw += rgb[i * 3:(i + 1) * 3] + bytes((alpha[i],))
        color = 6

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, color, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def _uri(blob, kind):
    return 'data:%s;base64,%s' % (kind, base64.b64encode(blob).decode('ascii'))


def _sheet(data, kind):
    sh = Sheet()
    sh.items.append(('im', 20, 30, 40, 16, data, kind))
    return sh


def _image_rgb(pdf, width):
    marker = ('/Subtype /Image /Width %d' % width).encode('ascii')
    at = 0
    while True:
        at = pdf.find(marker, at + 1)
        assert at > 0
        window = pdf[at:at + 220]
        if b'/DeviceRGB' in window:
            break
    length = int(window.split(b'/Length ', 1)[1].split()[0].rstrip(b'>'))
    start = pdf.find(b'stream\n', at) + len(b'stream\n')
    return zlib.decompress(pdf[start:start + length])


def test_pdf_draws_png_pixels(tmp_path):
    rgb = bytes([
        255, 0, 0, 0, 255, 0,
        0, 0, 255, 255, 255, 255,
    ])
    png = _png(2, 2, rgb)
    path = tmp_path / 'logo.pdf'
    missing = write_pdf([_sheet(_uri(png, 'image/png'), 'png')], str(path))
    data = path.read_bytes()
    assert missing == []
    assert b'/Subtype /Image' in data
    assert b' Do' in data
    assert _image_rgb(data, 2) == rgb


def test_pdf_keeps_png_transparency(tmp_path):
    png = _png(1, 1, bytes([10, 20, 30]), alpha=bytes([128]))
    path = tmp_path / 'alpha.pdf'
    write_pdf([_sheet(_uri(png, 'image/png'), 'png')], str(path))
    data = path.read_bytes()
    assert b'/SMask' in data
    assert _image_rgb(data, 1) == bytes([10, 20, 30])


def test_pdf_draws_svg_logo_as_vectors(tmp_path):
    path = tmp_path / 'svg.pdf'
    missing = write_pdf([_sheet(SVG, 'svg')], str(path))
    data = path.read_bytes()
    assert missing == []
    assert b'/Subtype /Image' not in data
    assert b' 0.110 0.110 0.110 rg' in data or b'0.110 0.110 0.110 rg' in data
    assert b'Tj' in data


def test_sheet_pdf_includes_the_template_logo(tmp_path):
    doc = execute(None, 'add_sheet', {'id': 's1', 'size': 'B'})['document']
    tpl = set_logo(default_template('B'), 'mark.svg', SVG)
    loaded = DrawingDocument.from_dict(attach_template(doc, tpl))
    path = tmp_path / 'sheet.pdf'
    missing = write_pdf(render_sheets(loaded), str(path))
    data = path.read_bytes()
    assert missing == []
    assert b'Tj' in data
    assert b'0.110 0.110 0.110 rg' in data
