#!/usr/bin/env python3
"""
Simple HTTP server for handling file saving from draw.io and serving static files
This server receives files via POST, saves them server-side, and serves static web content
"""

import os
import json
import datetime
import mimetypes
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default server configuration
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 8080
DEFAULT_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'main', 'webapp')
DEFAULT_SAVE_DIR = os.path.join(os.path.dirname(__file__), 'saved_files')

# Global configuration variables (will be set by parse_args)
HOST = DEFAULT_HOST
PORT = DEFAULT_PORT
STATIC_DIR = DEFAULT_STATIC_DIR
SAVE_DIR = DEFAULT_SAVE_DIR

class FileHandler(BaseHTTPRequestHandler):
    def _get_content_type(self, path):
        """Get content type for a file based on its extension"""
        content_type, _ = mimetypes.guess_type(path)
        if content_type is None:
            content_type = 'application/octet-stream'
        return content_type
    
    def _serve_static_file(self, file_path):
        """Serve a static file from the filesystem"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', self._get_content_type(file_path))
            self.send_header('Content-Length', str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            
        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Content-Type', 'text/html')
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b'<html><body><h1>404 Not Found</h1></body></html>')
        except Exception as e:
            logger.error(f"Error serving static file {file_path}: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b'<html><body><h1>500 Internal Server Error</h1></body></html>')
    def _set_cors_headers(self):
        """Set CORS headers for cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        
    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_HEAD(self):
        """Handle HEAD requests (same as GET but without body)"""
        # Save the original wfile to restore later
        original_wfile = self.wfile
        
        # Create a dummy wfile that discards all writes
        class DummyWfile:
            def write(self, data):
                pass
        
        self.wfile = DummyWfile()
        try:
            self.do_GET()
        finally:
            self.wfile = original_wfile
        """Handle preflight CORS requests"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for file saving"""
        try:
            parsed_path = urlparse(self.path)
            
            if parsed_path.path == '/save':
                self._handle_save_file()
            else:
                self._send_json_response(404, {'error': 'Endpoint not found'})
                
        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self._send_json_response(500, {'error': 'Internal server error'})
    
    def _handle_save_file(self):
        """Handle file saving request"""
        try:
            # Read request data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json_response(400, {'error': 'No data received'})
                return
                
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parse JSON data
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self._send_json_response(400, {'error': 'Invalid JSON data'})
                return
            
            # Validate required fields
            if 'filename' not in data or 'content' not in data:
                self._send_json_response(400, {'error': 'Missing filename or content'})
                return
            
            filename = data['filename']
            content = data['content']
            
            # Ensure save directory exists
            if not os.path.exists(SAVE_DIR):
                os.makedirs(SAVE_DIR)
            
            # Generate unique filename if needed
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            if not filename.endswith('.xml') and not filename.endswith('.drawio'):
                filename = f"{filename}.drawio"
            
            # Add timestamp to avoid conflicts
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{timestamp}{ext}"
            file_path = os.path.join(SAVE_DIR, unique_filename)
            
            # Save file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"File saved: {file_path}")
            
            self._send_json_response(200, {
                'success': True,
                'message': 'File saved successfully',
                'filename': unique_filename,
                'path': file_path,
                'timestamp': timestamp
            })
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            self._send_json_response(500, {'error': f'Failed to save file: {str(e)}'})
    
    def do_GET(self):
        """Handle GET requests for API endpoints and static file serving"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            # Handle API endpoints first
            if path == '/health':
                self._send_json_response(200, {'status': 'ok', 'message': 'Server is running'})
                return
            elif path == '/list':
                self._handle_list_files()
                return
            elif path.startswith('/open/'):
                # Handle opening saved files - extract filename from path
                filename = path[6:]  # Remove '/open/' prefix
                self._handle_open_saved_file(filename)
                return
            
            # Handle static file serving
            # Remove leading slash and handle empty path (root)
            if path == '/' or path == '':
                # Serve index.html for root requests
                file_path = os.path.join(STATIC_DIR, 'index.html')
            else:
                # Remove leading slash
                relative_path = path.lstrip('/')
                file_path = os.path.join(STATIC_DIR, relative_path)
            
            # Security check: ensure the file is within STATIC_DIR
            try:
                real_static_dir = os.path.realpath(STATIC_DIR)
                real_file_path = os.path.realpath(file_path)
                if not real_file_path.startswith(real_static_dir):
                    self.send_response(403)
                    self.send_header('Content-Type', 'text/html')
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(b'<html><body><h1>403 Forbidden</h1></body></html>')
                    return
            except Exception as e:
                logger.error(f"Error checking file path security: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'text/html')
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b'<html><body><h1>500 Internal Server Error</h1></body></html>')
                return
            
            # Check if file exists and serve it
            if os.path.isfile(file_path):
                self._serve_static_file(file_path)
            else:
                # If it's a directory, try to serve index.html from it
                if os.path.isdir(file_path):
                    index_path = os.path.join(file_path, 'index.html')
                    if os.path.isfile(index_path):
                        self._serve_static_file(index_path)
                    else:
                        self.send_response(404)
                        self.send_header('Content-Type', 'text/html')
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>404 Not Found</h1></body></html>')
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'text/html')
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(b'<html><body><h1>404 Not Found</h1></body></html>')
                
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b'<html><body><h1>500 Internal Server Error</h1></body></html>')
    
    def _handle_list_files(self):
        """List saved files"""
        try:
            if not os.path.exists(SAVE_DIR):
                files = []
            else:
                files = []
                for filename in os.listdir(SAVE_DIR):
                    if filename.endswith(('.xml', '.drawio')):
                        file_path = os.path.join(SAVE_DIR, filename)
                        stat = os.stat(file_path)
                        files.append({
                            'filename': filename,
                            'size': stat.st_size,
                            'modified': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
            
            self._send_json_response(200, {'files': files})
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            self._send_json_response(500, {'error': f'Failed to list files: {str(e)}'})
    
    def _handle_open_saved_file(self, filename):
        """Serve a saved file for opening"""
        try:
            # Security check: ensure filename doesn't contain path traversal
            if '..' in filename or '/' in filename or '\\' in filename:
                self.send_response(400)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b'Invalid filename')
                return
            
            # Only allow specific file extensions
            if not filename.endswith(('.xml', '.drawio')):
                self.send_response(400)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b'Invalid file type')
                return
            
            file_path = os.path.join(SAVE_DIR, filename)
            
            if not os.path.exists(file_path):
                self.send_response(404)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b'File not found')
                return
            
            # Read and return file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/xml')
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error opening saved file {filename}: {e}")
            self.send_response(500)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b'Internal server error')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='HTTP server for draw.io file saving and static content serving',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                                    # Use defaults (localhost:8080, serve src/main/webapp)
  %(prog)s --port 3000                       # Custom port
  %(prog)s --host 0.0.0.0 --port 8080        # Listen on all interfaces
  %(prog)s --static-dir /path/to/webapp      # Custom static directory
  %(prog)s --static-dir ./my-webapp --port 3000  # Custom directory and port
        ''')
    
    parser.add_argument('--host', 
                       default=DEFAULT_HOST, 
                       help=f'Host to bind to (default: {DEFAULT_HOST})')
    parser.add_argument('--port', 
                       type=int, 
                       default=DEFAULT_PORT, 
                       help=f'Port to bind to (default: {DEFAULT_PORT})')
    parser.add_argument('--static-dir', 
                       default=DEFAULT_STATIC_DIR, 
                       help=f'Directory to serve static files from (default: {DEFAULT_STATIC_DIR})')
    parser.add_argument('--save-dir',
                       default=DEFAULT_SAVE_DIR,
                       help=f'Directory to save uploaded files to (default: {DEFAULT_SAVE_DIR})')
    
    return parser.parse_args()

def run_server():
    """Start the HTTP server"""
    global HOST, PORT, STATIC_DIR, SAVE_DIR
    
    # Parse command line arguments
    args = parse_args()
    HOST = args.host
    PORT = args.port
    STATIC_DIR = os.path.abspath(args.static_dir)
    SAVE_DIR = os.path.abspath(args.save_dir)
    
    # Validate static directory exists
    if not os.path.exists(STATIC_DIR):
        logger.error(f"Static directory does not exist: {STATIC_DIR}")
        return 1
    
    if not os.path.isdir(STATIC_DIR):
        logger.error(f"Static path is not a directory: {STATIC_DIR}")
        return 1
    
    server = HTTPServer((HOST, PORT), FileHandler)
    logger.info(f"Server starting on {HOST}:{PORT}")
    logger.info(f"Static files served from: {STATIC_DIR}")
    logger.info(f"Uploaded files will be saved to: {SAVE_DIR}")
    logger.info("Available endpoints:")
    logger.info("  GET / - Serve static files from static directory")
    logger.info("  POST /save - Save a file")
    logger.info("  GET /health - Health check")
    logger.info("  GET /list - List saved files")
    logger.info("  GET /open/{filename} - Open a saved file")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        server.shutdown()
    
    return 0

if __name__ == '__main__':
    exit_code = run_server()
    exit(exit_code)