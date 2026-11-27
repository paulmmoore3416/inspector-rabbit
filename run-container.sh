#!/usr/bin/env bash
# Run Inspector Rabbit in a locked-down container.
#
#   ./run-container.sh            build (first time) and run
#   ./run-container.sh --rebuild  force a rebuild
#   IR_TOR=0 ./run-container.sh   run without the built-in Tor client
#
# Isolation applied:
#   - rootless Podman preferred (Docker works too, as uid 1000)
#   - read-only root filesystem, tmpfs /tmp, all Linux capabilities dropped,
#     no-new-privileges, no host home directory, no host network
#   - app data (settings, cases, evidence) lives in a private named volume
#   - only ~/InspectorRabbit-exports is shared with the host
#   - Wayland socket only (X11 is refused unless IR_ALLOW_X11=1, because an
#     X11 socket lets any client read keystrokes from the whole desktop)
set -euo pipefail

IMAGE="localhost/inspector-rabbit:1.6.0"
VOLUME="inspector-rabbit-data"
EXPORTS="${IR_EXPORTS:-$HOME/InspectorRabbit-exports}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if command -v podman >/dev/null 2>&1; then
    ENGINE=podman
    USERNS=(--userns=keep-id:uid=1000,gid=1000)
elif command -v docker >/dev/null 2>&1; then
    ENGINE=docker
    USERNS=(--user 1000:1000)
    echo "note: using Docker. Rootless Podman isolates better: sudo apt install podman" >&2
else
    echo "error: install podman (recommended) or docker" >&2
    exit 1
fi

if [[ "${1:-}" == "--rebuild" ]] || ! $ENGINE image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "Building $IMAGE ..." >&2
    $ENGINE build -t "$IMAGE" -f "$HERE/container/Containerfile" "$HERE"
fi

mkdir -p "$EXPORTS"
chmod 700 "$EXPORTS"

DISPLAY_ARGS=()
if [[ -n "${WAYLAND_DISPLAY:-}" && -S "${XDG_RUNTIME_DIR:-/nonexistent}/$WAYLAND_DISPLAY" ]]; then
    DISPLAY_ARGS+=(
        -e QT_QPA_PLATFORM=wayland
        -e WAYLAND_DISPLAY=wayland-0
        -e XDG_RUNTIME_DIR=/tmp/xdg
        -v "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:/tmp/xdg/wayland-0:ro"
    )
elif [[ "${IR_ALLOW_X11:-0}" == "1" && -n "${DISPLAY:-}" ]]; then
    echo "warning: X11 mode — the container can observe input to other X11 windows" >&2
    DISPLAY_ARGS+=(-e QT_QPA_PLATFORM=xcb -e DISPLAY="$DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix:ro)
else
    echo "error: no Wayland session found. Log into a Wayland session, or set IR_ALLOW_X11=1 to accept X11's weaker isolation." >&2
    exit 1
fi

exec $ENGINE run --rm -it \
    --name inspector-rabbit \
    "${USERNS[@]}" \
    --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,size=512m,mode=1777 \
    --cap-drop=ALL \
    --security-opt no-new-privileges \
    --pids-limit 512 \
    --memory 2g \
    -e IR_TOR="${IR_TOR:-1}" \
    -v "$VOLUME:/home/rabbit" \
    -v "$EXPORTS:/home/rabbit/exports" \
    "${DISPLAY_ARGS[@]}" \
    "$IMAGE"
