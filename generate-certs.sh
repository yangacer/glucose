#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/certs"
CA_DIR="${CERTS_DIR}/ca"
SERVER_DIR="${CERTS_DIR}/server"
CLIENTS_DIR="${CERTS_DIR}/clients"

AUTO_MODE=false
CLIENT_ONLY=false
CLIENT_NAME="client"

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Generate self-signed certificates for mTLS authentication"
    echo ""
    echo "Options:"
    echo "  --auto              Non-interactive mode with default values"
    echo "  --client-only       Generate only a new client certificate"
    echo "  --name NAME         Client certificate name (default: 'client')"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Interactive mode, generate all certs"
    echo "  $0 --auto                             # Auto mode with defaults"
    echo "  $0 --client-only --name john-doe      # Generate only client cert for john-doe"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --client-only)
            CLIENT_ONLY=true
            shift
            ;;
        --name)
            CLIENT_NAME="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ "$AUTO_MODE" = true ]; then
        eval "$var_name='$default'"
    else
        read -p "$prompt [$default]: " input
        eval "$var_name=\${input:-$default}"
    fi
}

generate_ca() {
    echo "=== Generating Certificate Authority (CA) ==="
    mkdir -p "$CA_DIR"
    
    prompt_input "CA Common Name" "Glucose Monitor CA" CA_CN
    prompt_input "Organization" "Glucose Monitor" CA_ORG
    prompt_input "Country (2-letter)" "US" CA_COUNTRY
    
    echo "Generating CA private key..."
    openssl genrsa -out "$CA_DIR/ca-key.pem" 4096
    chmod 600 "$CA_DIR/ca-key.pem"
    
    echo "Generating CA certificate..."
    openssl req -new -x509 -days 3650 -key "$CA_DIR/ca-key.pem" \
        -out "$CA_DIR/ca-cert.pem" \
        -subj "/C=$CA_COUNTRY/O=$CA_ORG/CN=$CA_CN"
    
    echo "CA certificate generated: $CA_DIR/ca-cert.pem"
}

generate_server() {
    echo ""
    echo "=== Generating Server Certificate ==="
    mkdir -p "$SERVER_DIR"
    
    prompt_input "Server Common Name" "localhost" SERVER_CN
    prompt_input "Organization" "Glucose Monitor" SERVER_ORG
    prompt_input "Country (2-letter)" "US" SERVER_COUNTRY
    prompt_input "Server IP address (optional, press Enter to skip)" "" SERVER_IP
    
    echo "Generating server private key..."
    openssl genrsa -out "$SERVER_DIR/server-key.pem" 4096
    chmod 600 "$SERVER_DIR/server-key.pem"
    
    echo "Generating server certificate signing request..."
    openssl req -new -key "$SERVER_DIR/server-key.pem" \
        -out "$SERVER_DIR/server-csr.pem" \
        -subj "/C=$SERVER_COUNTRY/O=$SERVER_ORG/CN=$SERVER_CN"
    
    echo "Creating server certificate extensions..."
    cat > "$SERVER_DIR/server-ext.cnf" <<EOF
subjectAltName = @alt_names
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
IP.3 = 0.0.0.0
EOF
    
    # Add custom IP if provided
    if [ -n "$SERVER_IP" ]; then
        echo "IP.4 = $SERVER_IP" >> "$SERVER_DIR/server-ext.cnf"
        echo "Added IP.4 = $SERVER_IP to certificate"
    fi
    
    echo "Signing server certificate with CA..."
    openssl x509 -req -days 730 -in "$SERVER_DIR/server-csr.pem" \
        -CA "$CA_DIR/ca-cert.pem" -CAkey "$CA_DIR/ca-key.pem" \
        -CAcreateserial -out "$SERVER_DIR/server-cert.pem" \
        -extfile "$SERVER_DIR/server-ext.cnf"
    
    rm "$SERVER_DIR/server-csr.pem" "$SERVER_DIR/server-ext.cnf"
    echo "Server certificate generated: $SERVER_DIR/server-cert.pem"
}

generate_client() {
    local name="$1"
    
    echo ""
    echo "=== Generating Client Certificate: $name ==="
    mkdir -p "$CLIENTS_DIR"
    
    if [ "$AUTO_MODE" = true ]; then
        CLIENT_CN="$name"
        CLIENT_ORG="Glucose Monitor"
        CLIENT_COUNTRY="US"
    else
        prompt_input "Client Common Name" "$name" CLIENT_CN
        prompt_input "Organization" "Glucose Monitor" CLIENT_ORG
        prompt_input "Country (2-letter)" "US" CLIENT_COUNTRY
    fi
    
    echo "Generating client private key..."
    openssl genrsa -out "$CLIENTS_DIR/client-${name}-key.pem" 4096
    chmod 600 "$CLIENTS_DIR/client-${name}-key.pem"
    
    echo "Generating client certificate signing request..."
    openssl req -new -key "$CLIENTS_DIR/client-${name}-key.pem" \
        -out "$CLIENTS_DIR/client-${name}-csr.pem" \
        -subj "/C=$CLIENT_COUNTRY/O=$CLIENT_ORG/CN=$CLIENT_CN"
    
    echo "Signing client certificate with CA..."
    openssl x509 -req -days 365 -in "$CLIENTS_DIR/client-${name}-csr.pem" \
        -CA "$CA_DIR/ca-cert.pem" -CAkey "$CA_DIR/ca-key.pem" \
        -CAcreateserial -out "$CLIENTS_DIR/client-${name}-cert.pem"
    
    rm "$CLIENTS_DIR/client-${name}-csr.pem"
    
    echo "Generating PKCS#12 bundle for browser import..."
    if [ "$AUTO_MODE" = true ]; then
        PKCS12_PASS=""
        openssl pkcs12 -export -passout pass: \
            -in "$CLIENTS_DIR/client-${name}-cert.pem" \
            -inkey "$CLIENTS_DIR/client-${name}-key.pem" \
            -out "$CLIENTS_DIR/client-${name}.p12" \
            -name "Glucose Monitor Client: $name"
    else
        openssl pkcs12 -export \
            -in "$CLIENTS_DIR/client-${name}-cert.pem" \
            -inkey "$CLIENTS_DIR/client-${name}-key.pem" \
            -out "$CLIENTS_DIR/client-${name}.p12" \
            -name "Glucose Monitor Client: $name"
    fi
    
    echo "Client certificate generated:"
    echo "  PEM format: $CLIENTS_DIR/client-${name}-cert.pem"
    echo "  PKCS#12 format: $CLIENTS_DIR/client-${name}.p12"
}

verify_openssl() {
    if ! command -v openssl &> /dev/null; then
        echo "Error: openssl is not installed"
        echo "Please install openssl and try again"
        exit 1
    fi
}

main() {
    verify_openssl
    
    echo "Glucose Monitor - mTLS Certificate Generator"
    echo "=============================================="
    echo ""
    
    if [ "$CLIENT_ONLY" = true ]; then
        if [ ! -f "$CA_DIR/ca-cert.pem" ] || [ ! -f "$CA_DIR/ca-key.pem" ]; then
            echo "Error: CA certificate not found. Please run without --client-only first."
            exit 1
        fi
        generate_client "$CLIENT_NAME"
    else
        generate_ca
        generate_server
        generate_client "$CLIENT_NAME"
    fi
    
    echo ""
    echo "=== Certificate Generation Complete ==="
    echo ""
    echo "Generated files:"
    echo "  CA Certificate:     $CA_DIR/ca-cert.pem"
    echo "  Server Certificate: $SERVER_DIR/server-cert.pem"
    echo "  Server Key:         $SERVER_DIR/server-key.pem"
    echo "  Client Certificate: $CLIENTS_DIR/client-${CLIENT_NAME}-cert.pem"
    echo "  Client Key:         $CLIENTS_DIR/client-${CLIENT_NAME}-key.pem"
    echo "  Client PKCS#12:     $CLIENTS_DIR/client-${CLIENT_NAME}.p12"
    echo ""
    echo "Next steps:"
    echo "1. Start the server with: python3 server.py"
    echo "2. Configure your client - see CLIENT.md for instructions"
    echo "3. To generate additional client certificates, run:"
    echo "   $0 --client-only --name <client-name>"
}

main
