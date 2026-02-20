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
