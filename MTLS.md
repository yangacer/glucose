# mTLS Quick Start Guide

## Generate Certificates

```bash
./generate-certs.sh
```

This will create:
- CA certificate and key
- Server certificate and key
- Client certificate and key (default client)

## Start Server

```bash
# With mTLS enabled (default, port 8443)
python3 server.py

# Custom port
PORT=9000 python3 server.py

# Without mTLS (development mode)
MTLS_ENABLED=false python3 server.py

# Custom port without mTLS
PORT=8080 MTLS_ENABLED=false python3 server.py
```

## Test Configuration

```bash
./test-mtls.sh
```

## Configure Client

See [CLIENT.md](CLIENT.md) for detailed instructions on:
- Browser setup (Chrome, Firefox, Safari)
- Command-line tools (curl, wget)
- Programming languages (Python, Node.js)

## Quick curl Test

```bash
curl https://localhost:8443/ \
  --cert certs/clients/client-client-cert.pem \
  --key certs/clients/client-client-key.pem \
  --cacert certs/ca/ca-cert.pem
```

## Generate Additional Client Certificates

```bash
./generate-certs.sh --client-only --name "john-doe"
```

## Troubleshooting

1. **Certificate not found**: Run `./generate-certs.sh` first
2. **Connection refused**: Check if server is running
3. **Certificate expired**: Regenerate certificates
4. **Browser doesn't prompt**: Import client certificate (see CLIENT.md)

## Security Notes

- Keep private keys secure (permissions: 600)
- Monitor certificate expiration (server logs warnings)
- Use proper CA for production (not self-signed)
- Never commit private keys to version control
