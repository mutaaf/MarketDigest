#!/bin/bash
# Publishes azizfamily.local on the LAN via a Bonjour proxy record, without
# changing the Mac's hostname. Run by launchd (com.azizfamily.mdns).
#
# dns-sd -P registers a proxy: hostname azizfamily.local -> current LAN IP,
# advertised over mDNS. It must stay running to keep the record alive, so this
# wrapper supervises it and re-registers whenever the IP changes (wifi hop,
# DHCP renewal).

HOSTNAME="azizfamily.local"
PORT=80
CHILD=""

current_ip() {
  for iface in en0 en1; do
    ip=$(ipconfig getifaddr "$iface" 2>/dev/null)
    [ -n "$ip" ] && { echo "$ip"; return; }
  done
  echo ""
}

cleanup() { [ -n "$CHILD" ] && kill "$CHILD" 2>/dev/null; exit 0; }
trap cleanup INT TERM

LAST_IP=""
while true; do
  IP=$(current_ip)
  if [ -n "$IP" ] && [ "$IP" != "$LAST_IP" ]; then
    [ -n "$CHILD" ] && kill "$CHILD" 2>/dev/null
    dns-sd -P "Aziz Family Portal" _http._tcp local "$PORT" "$HOSTNAME" "$IP" &
    CHILD=$!
    LAST_IP="$IP"
    echo "$(date '+%F %T') publishing $HOSTNAME -> $IP"
  elif [ -n "$CHILD" ] && ! kill -0 "$CHILD" 2>/dev/null; then
    LAST_IP=""  # dns-sd died; force re-register next loop
  fi
  sleep 30
done
