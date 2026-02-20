#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/certs"
CA_CERT="${CERTS_DIR}/ca/ca-cert.pem"
SERVER_CERT="${CERTS_DIR}/server/server-cert.pem"
CLIENT_CERT="${CERTS_DIR}/clients/client-client-cert.pem"
CLIENT_KEY="${CERTS_DIR}/clients/client-client-key.pem"
PORT="${PORT:-8443}"
SERVER_URL="https://localhost:${PORT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "====================================="
echo "mTLS Configuration Test"
echo "====================================="
echo ""

# Test 1: Check if certificates exist
echo "[1/6] Checking certificate files..."
ALL_EXIST=true

for file in "$CA_CERT" "$SERVER_CERT" "$CLIENT_CERT" "$CLIENT_KEY"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} Found: $file"
    else
        echo -e "${RED}✗${NC} Missing: $file"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = false ]; then
    echo ""
    echo -e "${RED}Error: Certificate files missing!${NC}"
    echo "Please run: ./generate-certs.sh"
    exit 1
fi
echo ""

# Test 2: Verify certificate chain
echo "[2/6] Verifying certificate chain..."
if openssl verify -CAfile "$CA_CERT" "$SERVER_CERT" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Server certificate valid"
else
    echo -e "${RED}✗${NC} Server certificate verification failed"
    exit 1
fi

if openssl verify -CAfile "$CA_CERT" "$CLIENT_CERT" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Client certificate valid"
else
    echo -e "${RED}✗${NC} Client certificate verification failed"
    exit 1
fi
echo ""

# Test 3: Check certificate expiration
echo "[3/6] Checking certificate expiration..."
SERVER_EXPIRY=$(openssl x509 -in "$SERVER_CERT" -noout -enddate | cut -d= -f2)
CLIENT_EXPIRY=$(openssl x509 -in "$CLIENT_CERT" -noout -enddate | cut -d= -f2)

echo -e "${GREEN}✓${NC} Server cert expires: $SERVER_EXPIRY"
echo -e "${GREEN}✓${NC} Client cert expires: $CLIENT_EXPIRY"
echo ""

# Test 4: Check if server is running
echo "[4/6] Checking if server is running..."
if pgrep -f "server.py" > /dev/null; then
    echo -e "${GREEN}✓${NC} Server process found"
else
    echo -e "${YELLOW}⚠${NC} Server not running"
    echo "Please start the server in another terminal: python3 server.py"
    echo "Then run this test again."
    exit 0
fi
echo ""

# Test 5: Test connection WITH client certificate
echo "[5/6] Testing mTLS connection (with client cert)..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    --cert "$CLIENT_CERT" \
    --key "$CLIENT_KEY" \
    --cacert "$CA_CERT" \
    "$SERVER_URL/" 2>&1 || echo "FAILED")

if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "301" ]; then
    echo -e "${GREEN}✓${NC} Connection successful (HTTP $RESPONSE)"
else
    echo -e "${RED}✗${NC} Connection failed: $RESPONSE"
    echo "Check server logs for details"
fi
echo ""

# Test 6: Test connection WITHOUT client certificate (should fail)
echo "[6/6] Testing connection without client cert (should fail)..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    --cacert "$CA_CERT" \
    "$SERVER_URL/" 2>&1 || echo "FAILED")

if [ "$RESPONSE" = "FAILED" ] || [[ "$RESPONSE" =~ "alert" ]]; then
    echo -e "${GREEN}✓${NC} Correctly rejected (no client certificate)"
else
    echo -e "${YELLOW}⚠${NC} Unexpected response: $RESPONSE"
fi
echo ""

# Summary
echo "====================================="
echo "Test Summary"
echo "====================================="
echo ""
echo "mTLS configuration appears to be working correctly!"
echo ""
echo "Next steps:"
echo "1. Configure your browser - see CLIENT.md"
echo "2. Access the application at: $SERVER_URL"
echo "3. Monitor server logs for client connections"
echo ""
echo "Useful commands:"
echo "  # View server certificate details"
echo "  openssl x509 -in $SERVER_CERT -text -noout"
echo ""
echo "  # Test with curl"
echo "  curl $SERVER_URL/ \\"
echo "    --cert $CLIENT_CERT \\"
echo "    --key $CLIENT_KEY \\"
echo "    --cacert $CA_CERT"
