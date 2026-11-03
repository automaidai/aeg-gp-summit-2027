"""Local preview including Vercel-style API routing. Run python3 dev.py."""
import importlib.util
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
spec=importlib.util.spec_from_file_location('summit_api',Path(__file__).parent/'api'/'app.py')
api=importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
class Preview(api.handler,SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(Path(__file__).parent/'public'),**kwargs)
    def do_GET(self):
        if self.path.startswith('/api/app'):
            return api.handler.do_GET(self)
        return SimpleHTTPRequestHandler.do_GET(self)
if __name__=='__main__':
    print('Summit preview: http://127.0.0.1:4173',flush=True)
    ThreadingHTTPServer(('127.0.0.1',4173),Preview).serve_forever()
