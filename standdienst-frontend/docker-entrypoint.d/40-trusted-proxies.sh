#!/bin/sh
# Erzeugt /etc/nginx/trusted_proxies.conf aus TRUSTED_PROXIES (IP/CIDR, durch
# Komma oder Leerzeichen getrennt). Nur von diesen Adressen wird X-Forwarded-For
# übernommen; nginx setzt $remote_addr dann auf die echte Client-IP und reicht
# sie an die API weiter. Leer = kein externer Reverse-Proxy vor dem Container.
set -eu

OUT=/etc/nginx/trusted_proxies.conf
: > "$OUT"

if [ -z "${TRUSTED_PROXIES:-}" ]; then
    echo "$0: TRUSTED_PROXIES nicht gesetzt – X-Forwarded-For wird nicht ausgewertet"
    exit 0
fi

for proxy in $(echo "$TRUSTED_PROXIES" | tr ',' ' '); do
    case "$proxy" in
        *[!0-9A-Fa-f.:/]*)
            echo "$0: Ungültiger Eintrag in TRUSTED_PROXIES: '$proxy' (erwartet IP oder CIDR)" >&2
            exit 1
            ;;
    esac
    echo "set_real_ip_from $proxy;" >> "$OUT"
done
echo "real_ip_header X-Forwarded-For;" >> "$OUT"
echo "real_ip_recursive on;" >> "$OUT"

echo "$0: Vertrauenswürdige Reverse-Proxys: $TRUSTED_PROXIES"
