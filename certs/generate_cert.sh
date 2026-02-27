#!/bin/bash
# Generate a self-signed SSL certificate for local HTTPS development.
# Run this script once from the certs/ directory.

openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
    -subj "/C=US/ST=Local/L=Local/O=Daycare/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Certificate generated: cert.pem, key.pem"
