# encoding: utf-8
from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
from web.config import partitions, address, port

files = {}

class MyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not files:
            for partition in partitions:
                _ = partition.get_fdt()
                files.update({path: (obj.cluster_list,
                                     obj.create_time.timestamp())
                              for path, obj in _.items()})
        self.wfile.write(bytes(json.dumps(files), encoding='ascii'))


httpd = HTTPServer((address, port), MyHandler)
