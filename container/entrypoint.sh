#!/bin/sh
# Inspector Rabbit container entrypoint
set -eu

mkdir -p "$HOME/exports" "$HOME/.config"

# Start the container-private Tor client unless disabled (IR_TOR=0)
if [ "${IR_TOR:-1}" = "1" ]; then
    mkdir -p /tmp/tor-data && chmod 700 /tmp/tor-data
    tor -f /etc/tor/torrc --RunAsDaemon 1 >/dev/null 2>&1 || echo "warning: tor failed to start" >&2
    # First run inside the container: default the app to Tor + kill switch
    SETTINGS="${INSPECTOR_RABBIT_SETTINGS:-$HOME/.inspector_rabbit_settings.json}"
    if [ ! -f "$SETTINGS" ]; then
        umask 077
        printf '{"proxy_mode": "tor", "kill_switch": true}\n' > "$SETTINGS"
    fi
    i=0
    while [ $i -lt 60 ] && ! grep -q "Bootstrapped 100%" /tmp/tor.log 2>/dev/null; do
        sleep 1; i=$((i+1))
    done
    grep -q "Bootstrapped 100%" /tmp/tor.log 2>/dev/null \
        && echo "tor: connected" >&2 \
        || echo "tor: still bootstrapping (kill switch blocks lookups until it is up)" >&2
fi

cd "$HOME"
exec "$@"
