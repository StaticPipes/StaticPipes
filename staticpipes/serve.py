import http.server
import socketserver


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


DIRECTORY = None


def server(directory_name, server_address, server_port):
    global DIRECTORY
    DIRECTORY = directory_name
    with socketserver.TCPServer((server_address, server_port), Handler) as httpd:
        print("serving at http://" + server_address + ":" + str(server_port))
        httpd.serve_forever()
