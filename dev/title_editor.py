"""Title block editor. Separate from the sheet editor.

  python dev/title_editor.py

Then open http://127.0.0.1:8766/
Templates are saved under formats/<size>.json in the folder you started from.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, 'SRDrawingPDF'))

from sheet2d.formats import (  # noqa: E402
    FIELDS, SIZES, add_box, clear_logo, default_template, load_template, move_box,
    remove_box, resize_box, save_template, set_logo, template_svg,
)

_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'title_editor.html')


class Editor(object):
    def __init__(self, folder):
        self.folder = folder
        self.template = default_template('B')
        self.note = ''

    def payload(self):
        return {
            'template': self.template,
            'svg': template_svg(self.template, {'project': '', 'title': 'TITLE FROM THE DESIGN'}),
            'sizes': list(SIZES),
            'fields': list(FIELDS),
            'note': self.note,
        }

    def command(self, name, args):
        args = args or {}
        tpl = self.template
        if name == 'boot':
            return self.payload()
        if name == 'size':
            self.template = self._stored(args.get('size') or 'B')
            self.note = 'Size %s' % self.template['size']
        elif name == 'move':
            self.template = move_box(tpl, args['id'], args['x'], args['y'])
            self.note = 'Moved %s' % args['id']
        elif name == 'resize':
            self.template = resize_box(tpl, args['id'], args['w'], args['h'])
            self.note = 'Resized %s' % args['id']
        elif name == 'add':
            self.template = add_box(tpl, field=args.get('field') or 'static', label=args.get('label') or 'NOTE')
            self.note = 'Added a box'
        elif name == 'remove':
            self.template = remove_box(tpl, args['id'])
            self.note = 'Removed %s' % args['id']
        elif name == 'logo':
            self.template = set_logo(tpl, args.get('name'), args.get('data'))
            self.note = 'Logo %s' % (args.get('name') or '')
        elif name == 'clear_logo':
            self.template = clear_logo(tpl)
            self.note = 'Logo removed'
        elif name == 'save':
            path = self._path(self.template['size'])
            save_template(self.template, path)
            self.note = 'Saved %s' % os.path.basename(path)
        elif name == 'load':
            self.template = self._stored(self.template['size'])
            self.note = 'Loaded %s' % self.template['size']
        else:
            raise ValueError('unknown command %r' % name)
        return self.payload()

    def _path(self, size):
        folder = os.path.join(self.folder, 'formats')
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, size + '.json')

    def _stored(self, size):
        path = self._path(size)
        if os.path.isfile(path):
            return load_template(path)
        return default_template(size)


def make_handler(editor):
    html = open(_HTML, encoding='utf-8').read()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            if urlparse(self.path).path in ('/', '/index.html'):
                body = html.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

        def do_POST(self):
            n = int(self.headers.get('Content-Length') or 0)
            try:
                msg = json.loads(self.rfile.read(n).decode('utf-8') or '{}')
                body = json.dumps(editor.command(msg.get('command'), msg.get('args'))).encode('utf-8')
                self.send_response(200)
            except ValueError as exc:
                body = json.dumps({'error': str(exc)}).encode('utf-8')
                self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main(argv):
    port = 8766
    if len(argv) > 1:
        port = int(argv[1])
    editor = Editor(os.getcwd())
    httpd = ThreadingHTTPServer(('127.0.0.1', port), make_handler(editor))
    print('Title block editor: http://127.0.0.1:%d/' % port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
