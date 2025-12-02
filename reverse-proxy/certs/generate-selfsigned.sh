#!/bin/sh
set -eu

CERT_DIR=${CERT_DIR:-/etc/nginx/certs}
CERT_FILE=${CERT_FILE:-$CERT_DIR/tls.crt}
KEY_FILE=${KEY_FILE:-$CERT_DIR/tls.key}
CONFIG_FILE=${CONFIG_FILE:-$CERT_DIR/openssl.cnf}
DAYS_VALID=${TLS_DAYS:-365}
DOMAINS=${TLS_DOMAINS:-localhost,127.0.0.1,adviseme.local}

# Append detected host IPs so the cert matches the machine we're on
HOST_IPS=$(hostname -I 2>/dev/null | tr -s ' ' || true)
for ip in $HOST_IPS; do
  ip=$(echo "$ip" | tr -d '[:space:]')
  if [ -z "$ip" ]; then
    continue
  fi
  case ",$DOMAINS," in
    *",$ip,"*) ;;
    *) DOMAINS="$DOMAINS,$ip" ;;
  esac
done

mkdir -p "$CERT_DIR"

cat > "$CONFIG_FILE" <<'EOF'
[req]
default_bits = 4096
prompt = no
default_md = sha256
req_extensions = v3_req
distinguished_name = dn

[dn]
C = US
ST = State
L = City
O = Adviseme
OU = Dev
CN = localhost

[v3_req]
subjectAltName = @alt_names

[alt_names]
EOF

IFS=','
dns_idx=1
ip_idx=1
for raw in $DOMAINS; do
  entry=$(echo "$raw" | tr -d '[:space:]')
  if [ -z "$entry" ]; then
    continue
  fi
  if echo "$entry" | grep -q ':'; then
    echo "IP.$ip_idx = $entry" >> "$CONFIG_FILE"
    ip_idx=$((ip_idx + 1))
  elif echo "$entry" | grep -Eq '^[0-9.]+$'; then
    echo "IP.$ip_idx = $entry" >> "$CONFIG_FILE"
    ip_idx=$((ip_idx + 1))
  else
    echo "DNS.$dns_idx = $entry" >> "$CONFIG_FILE"
    dns_idx=$((dns_idx + 1))
  fi
done
unset IFS

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
  echo "Using existing certificate in $CERT_DIR"
  exit 0
fi

echo "Generating self-signed certificate for: $DOMAINS"
openssl req \
  -x509 \
  -nodes \
  -days "$DAYS_VALID" \
  -newkey rsa:4096 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -config "$CONFIG_FILE"
