# Glucose Monitoring Dashboard

A personal health monitoring application for tracking feline glucose levels, insulin doses, nutrition intake, and health events. Features a web-based dashboard with charts, risk metrics, and a summary timesheet.

---

## Quick Start

```bash
# 1. Initialize the database
python3 init_db.py

# 2. Start the server (mTLS enabled by default, port 8443)
python3 server.py
```

Access `https://localhost:8443/` in your browser. For mTLS client setup, see [`CLIENT.md`](CLIENT.md).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8443` | Server port |
| `MTLS_ENABLED` | `true` | Enable mutual TLS |
| `DEBUG_STATIC` | `false` | Serve unminified JS (`index.html.dev`) for frontend debugging |
| `DB_PATH` | `glucose.db` | SQLite database file path |
| `CA_CERT` | `certs/ca/ca-cert.pem` | CA certificate path |
| `SERVER_CERT` | `certs/server/server-cert.pem` | Server certificate path |
| `SERVER_KEY` | `certs/server/server-key.pem` | Server private key path |

Common combinations:

```bash
# Disable mTLS (plain HTTP, useful for testing without certificates)
MTLS_ENABLED=false PORT=8080 python3 server.py

# Debug frontend JS without disabling mTLS
DEBUG_STATIC=true python3 server.py
```

---

## Development

### Requirements

- Python 3.8+ (standard library only — no pip dependencies)
- [terser](https://terser.org/) — for minifying JavaScript (`npm install -g terser`)

### Running Tests

```bash
python3 test_server.py
```

### Frontend Build

The frontend uses a dev/prod split. `static/index.html.dev` loads individual JS files for easy debugging; `static/index.html` loads the minified bundle.

```bash
# Build minified bundle (increments or sets version x.y.z)
./build-js.py x.y.z
```

This generates `static/js/release/app.min.js` and regenerates `static/index.html`. See [`DEPLOY.md`](DEPLOY.md) for full build workflow.

### mTLS Setup

```bash
# Generate self-signed certificates (CA + server + example client)
./generate-certs.sh
```

See [`MTLS.md`](MTLS.md) for quick start and [`CLIENT.md`](CLIENT.md) for per-browser/OS client configuration.

---

## DISCLAIMER

Any charts or data visualizations in this project are for demonstration
purposes only and do not reflect real patient data nor clinical outcomes.
They are generated using synthetic data and models to illustrate the
functionality of the application. Please do not use these visualizations for
clinical decision-making or any real-world applications. Always consult with a
healthcare professional for accurate medical advice and information.
