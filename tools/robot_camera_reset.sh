#!/usr/bin/env bash
set -euo pipefail

ROBOT_HOST="${ROBOT_HOST:-192.168.100.30}"
ROBOT_USER="${ROBOT_USER:-unitree}"
ROBOT_PASSWORD="${ROBOT_PASSWORD:-123}"
USB_DEVICE="${USB_DEVICE:-2-2.3}"

ASKPASS_FILE=""
cleanup() {
  if [[ -n "${ASKPASS_FILE}" ]]; then
    rm -f "${ASKPASS_FILE}"
  fi
}
trap cleanup EXIT

ssh_env=()
ssh_prefix=()
if [[ -n "${ROBOT_PASSWORD}" ]]; then
  ASKPASS_FILE="$(mktemp /tmp/robot_camera_reset_askpass.XXXXXX)"
  chmod 700 "${ASKPASS_FILE}"
  cat > "${ASKPASS_FILE}" <<'EOF'
#!/bin/sh
printf '%s\n' "${ROBOT_PASSWORD}"
EOF
  ssh_env=(
    "ROBOT_PASSWORD=${ROBOT_PASSWORD}"
    "SSH_ASKPASS=${ASKPASS_FILE}"
    "SSH_ASKPASS_REQUIRE=force"
    "DISPLAY=${DISPLAY:-:0}"
  )
  ssh_prefix=(setsid)
fi

echo "Resetting RealSense USB device ${USB_DEVICE} on ${ROBOT_USER}@${ROBOT_HOST}"
env "${ssh_env[@]}" "${ssh_prefix[@]}" ssh -o StrictHostKeyChecking=no "${ROBOT_USER}@${ROBOT_HOST}" "
set -e
echo '${ROBOT_PASSWORD}' | sudo -S sh -c 'echo 0 > /sys/bus/usb/devices/${USB_DEVICE}/authorized; sleep 2; echo 1 > /sys/bus/usb/devices/${USB_DEVICE}/authorized'
sleep 5
ls -l /dev/v4l/by-path 2>/dev/null || true
"

echo "Reset complete."
