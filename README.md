# Glucose Monitoring Server

```bash
# Start server with default configuration (mTLS on port 8443)
python3 server.py

# Start server on custom port
PORT=8080 python3 server.py

# Start server without mTLS (development mode)
MTLS_ENABLED=false python3 server.py
```

The server supports the following environment variables:
- `PORT`: Server port (default: 8443)
- `MTLS_ENABLED`: Enable/disable mTLS (default: true)
- `DB_PATH`: Database file path (default: glucose.db)
- `CA_CERT`: Path to CA certificate
- `SERVER_CERT`: Path to server certificate
- `SERVER_KEY`: Path to server private key

Access https://localhost:8443/ (or http://localhost:PORT if mTLS disabled) in your browser.


# DISCLAIMER:

Any charts or data visualizations in this project are for demonstration
purposes only and do not reflect real patient data nor clinical outcomes.
They are generated using synthetic data and models to illustrate the
functionality of the application. Please do not use these visualizations for
clinical decision-making or any real-world applications. Always consult with a
healthcare professional for accurate medical advice and information.

# Development

## Required Tools

- Python 3.8+
- terser: For minifying JavaScript

## Backend

All backend code is located in the `server.py` file. It intentionally uses only
the Python standard library to minimize dependencies and simplify deployment.

## Frontend

Frontend assets are located in the `static/` directory. The main entry point is
`static/index.html.dev`, which loads the necessary JavaScript and CSS files.
To minify JavaScript files for production, run the following command:

```bash
./build-js.sh x.y.z
```

where `x.y.z` is the version number to embed in the JavaScript code. This will
generate minified files in the `static/release/` directory and generate
`static/index.html` that references the minified assets.

When `MTLS_ENABLED` is set to `false`, the server will serve the
`static/index.html.dev` file, which references the unminified JavaScript files
for easier debugging during development.

When `MTLS_ENABLED` is set to `true`, the server will serve the
`static/index.html` file, which references the minified JavaScript files for
production use.
