import http.server
import socketserver
import os
import json
import urllib.parse
import logging
from datetime import datetime
from http import HTTPStatus
import pathlib
from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PORT = 3000
BASE_DIR = pathlib.Path(".")
STORAGE_DIR = BASE_DIR / "storage"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
IMG_DIR = STATIC_DIR / "img"

STORAGE_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
CSS_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)

logger.info(f"Storage directory: {STORAGE_DIR}")
logger.info(f"Templates directory: {TEMPLATES_DIR}")
logger.info(f"Static directory: {STATIC_DIR}")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
logger.info("Jinja2 environment initialized")

class WebServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html_file("index.html")
            case "/message.html":
                self.send_html_file("message.html")
            case "/static/css/style.css":
                self.send_static_file(CSS_DIR / "style.css", "text/css")
            case "/static/img/logo.png":
                self.send_static_file(IMG_DIR / "logo.png", "image/png")
            case "/read":
                self.send_read_page()
            case _:
                self.send_html_file("error.html", HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            parsed_data = urllib.parse.parse_qs(post_data)
            
            data = {
                "username": parsed_data.get("username", [""])[0],
                "message": parsed_data.get("message", [""])[0]
            }
            
            self.save_data(data)
            
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_html_file("error.html", HTTPStatus.NOT_FOUND)

    def send_html_file(self, filename, status=HTTPStatus.OK):
        try:
            template = env.get_template(filename)
            content = template.render().encode('utf-8')
            
            self.send_response(status)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logger.error(f"Error rendering template {filename}: {e}")
            try:
                template = env.get_template("error.html")
                content = template.render().encode('utf-8')
                self.send_response(HTTPStatus.NOT_FOUND)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                logger.error(f"Error rendering error template: {e}")
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.end_headers()

    def send_static_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as file:
                content = file.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            logger.error(f"Static file not found: {filepath}")
            self.send_html_file("error.html", HTTPStatus.NOT_FOUND)

    def save_data(self, data):
        storage_file = STORAGE_DIR / "data.json"
        
        try:
            if storage_file.exists():
                with open(storage_file, "r", encoding="utf-8") as file:
                    try:
                        storage_data = json.load(file)
                    except json.JSONDecodeError:
                        storage_data = {}
            else:
                storage_data = {}
                
            timestamp = str(datetime.now())
            storage_data[timestamp] = data
            
            with open(storage_file, "w", encoding="utf-8") as file:
                json.dump(storage_data, file, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def send_read_page(self):
        try:
            template_path = TEMPLATES_DIR / "read.html"
            if not template_path.exists():
                with open(template_path, "w", encoding="utf-8") as file:
                    file.write("""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Read Messages</title>
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="/static/css/style.css" />
  </head>
  <body>
    <header>
      <nav class="navbar navbar-expand navbar-dark bg-dark">
        <div class="container-fluid">
          <a class="navbar-brand" href="#">
            <img src="/static/img/logo.png" alt="logo" />
          </a>
          <div class="collapse navbar-collapse" id="navbarsExample02">
            <ul class="navbar-nav me-auto">
              <li class="nav-item">
                <a class="nav-link" aria-current="page" href="/">Home</a>
              </li>
              <li class="nav-item">
                <a class="nav-link" href="/message.html">Send message</a>
              </li>
              <li class="nav-item">
                <a class="nav-link active" href="/read">Read messages</a>
              </li>
            </ul>
          </div>
        </div>
      </nav>
      <div class="p-3 pb-md-4 mx-auto text-center">
        <h1 class="display-4 fw-normal">Messages</h1>
      </div>
    </header>
    <main class="container">
      <div class="row">
        <div class="col-12">
          {% if messages %}
            {% for timestamp, message in messages.items() %}
              <div class="card mb-3">
                <div class="card-header">
                  <strong>{{ message.username }}</strong> <small class="text-muted">{{ timestamp }}</small>
                </div>
                <div class="card-body">
                  <p class="card-text">{{ message.message }}</p>
                </div>
              </div>
            {% endfor %}
          {% else %}
            <div class="alert alert-info">No messages yet.</div>
          {% endif %}
        </div>
      </div>
    </main>
  </body>
</html>""")
            
            storage_file = STORAGE_DIR / "data.json"
            if storage_file.exists():
                with open(storage_file, "r", encoding="utf-8") as file:
                    try:
                        messages = json.load(file)
                    except json.JSONDecodeError:
                        messages = {}
            else:
                messages = {}
            
            template = env.get_template('read.html')
            content = template.render(messages=messages)
            
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error rendering read page: {e}")
            self.send_html_file("error.html", HTTPStatus.INTERNAL_SERVER_ERROR)

def run_server():
    logger.info(f"Starting server at http://localhost:{PORT}")
    handler = WebServerHandler
    httpd = socketserver.TCPServer(("", PORT), handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
        logger.info("Server stopped.")

if __name__ == "__main__":
    run_server()