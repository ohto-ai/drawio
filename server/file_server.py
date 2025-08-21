#!/usr/bin/env python3
"""
Simple HTTP server for handling file saving from draw.io
This server receives files via POST and saves them server-side
"""

import os
import json
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server configuration
HOST = 'localhost'
PORT = 8080
SAVE_DIR = os.path.join(os.path.dirname(__file__), 'saved_files')

class FileHandler(BaseHTTPRequestHandler):
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
    
    def do_OPTIONS(self):
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
        """Handle GET requests for file listing and health check"""
        try:
            parsed_path = urlparse(self.path)
            
            if parsed_path.path == '/health':
                self._send_json_response(200, {'status': 'ok', 'message': 'Server is running'})
            elif parsed_path.path == '/list':
                self._handle_list_files()
            else:
                self._send_json_response(404, {'error': 'Endpoint not found'})
                
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self._send_json_response(500, {'error': 'Internal server error'})
    
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

def run_server():
    """Start the HTTP server"""
    server = HTTPServer((HOST, PORT), FileHandler)
    logger.info(f"Server starting on {HOST}:{PORT}")
    logger.info(f"Files will be saved to: {SAVE_DIR}")
    logger.info("Available endpoints:")
    logger.info("  POST /save - Save a file")
    logger.info("  GET /health - Health check")
    logger.info("  GET /list - List saved files")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        server.shutdown()

if __name__ == '__main__':
    run_server()