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

