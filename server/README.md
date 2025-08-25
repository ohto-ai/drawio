# Draw.io Server

A simple HTTP server that provides both static file serving for the draw.io web application and API endpoints for file operations.

## Features

- **Static File Serving**: Serves the draw.io web application from `src/main/webapp` by default
- **File Management API**: Save and list draw.io diagrams on the server
- **Configurable**: Port and static directory can be customized via command line arguments
- **CORS Support**: Cross-origin requests are supported for API endpoints

## Usage

### Basic Usage

```bash
# Start server with defaults (localhost:8080, serve src/main/webapp)
python server/server.py
```

### Custom Configuration

```bash
# Custom port
python server/server.py --port 3000

# Listen on all interfaces
python server/server.py --host 0.0.0.0 --port 8080

# Custom static directory
python server/server.py --static-dir /path/to/webapp

# Multiple options
python server/server.py --host 0.0.0.0 --port 3000 --static-dir ./my-webapp
```

### Command Line Options

- `--host HOST`: Host to bind to (default: localhost)
- `--port PORT`: Port to bind to (default: 8080)
- `--static-dir STATIC_DIR`: Directory to serve static files from (default: src/main/webapp)
- `--save-dir SAVE_DIR`: Directory to save uploaded files to (default: server/saved_files)

## API Endpoints

- `GET /` - Serves the draw.io web application (index.html)
- `GET /<path>` - Serves static files from the configured static directory
- `POST /save` - Save a diagram file to the server
- `GET /health` - Health check endpoint
- `GET /list` - List saved diagram files

## Example

1. Start the server:
   ```bash
   python server/server.py
   ```

2. Open your browser and navigate to: `http://localhost:8080`

3. Create diagrams in the draw.io interface

4. Save diagrams to the server using the built-in save functionality