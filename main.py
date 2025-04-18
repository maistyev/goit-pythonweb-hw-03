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

# Configure logging
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

# Ensure storage directory exists
STORAGE_DIR.mkdir(exist_ok=True)
logger.info(f"Storage directory: {STORAGE_DIR}")

# Initialize Jinja2 environment
env = Environment(loader=FileSystemLoader('templates'))
logger.info("Jinja2 environment initialized")

class WebServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html_file("index.html")
            case "/message.html":
                self.send_html_file("message.html")
            case "/style.css":
                self.send_static("style.css", "text/css")
            case "/logo.png":
                self.send_static("logo.png", "image/png")
            case "/read":
                self.send_read_page()
            case _:
                self.send_html_file("error.html", HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            parsed_data = urllib.parse.parse_qs(post_data)
            
            # Convert parsed data to the required format
            data = {
                "username": parsed_data.get("username", [""])[0],
                "message": parsed_data.get("message", [""])[0]
            }
            
            # Save data to storage
            self.save_data(data)
            
            # Redirect to the main page
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_html_file("error.html", HTTPStatus.NOT_FOUND)

    def send_html_file(self, filename, status=HTTPStatus.OK):
        try:
            with open(filename, "rb") as file:
                content = file.read()
            self.send_response(status)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_html_file("error.html", HTTPStatus.NOT_FOUND)

    def send_static(self, filename, content_type):
        try:
            with open(filename, "rb") as file:
                content = file.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_html_file("error.html", HTTPStatus.NOT_FOUND)

    def save_data(self, data):
        # Load existing data
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
                
            # Add new data with timestamp
            timestamp = str(datetime.now())
            storage_data[timestamp] = data
            
            # Save updated data
            with open(storage_file, "w", encoding="utf-8") as file:
                json.dump(storage_data, file, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def send_read_page(self):
        try:
            # Create templates directory if it doesn't exist
            templates_dir = BASE_DIR / "templates"
            templates_dir.mkdir(exist_ok=True)
            
            # Create read.html template if it doesn't exist
            template_path = templates_dir / "read.html"
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
    <link rel="stylesheet" href="/style.css" />
  </head>
  <body>
    <header>
      <nav class="navbar navbar-expand navbar-dark bg-dark">
        <div class="container-fluid">
          <a class="navbar-brand" href="#">
            <img src="/logo.png" alt="logo" />
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
            
            # Load data from storage
            storage_file = STORAGE_DIR / "data.json"
            if storage_file.exists():
                with open(storage_file, "r", encoding="utf-8") as file:
                    try:
                        messages = json.load(file)
                    except json.JSONDecodeError:
                        messages = {}
            else:
                messages = {}
            
            # Render template
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