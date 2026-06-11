#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT_HOST="${ROBOT_HOST:-192.168.100.30}"
ROBOT_USER="${ROBOT_USER:-unitree}"
ROBOT_PASSWORD="${ROBOT_PASSWORD:-123}"
CONTAINER_NAME="${CONTAINER_NAME:-unitree-dex3-dev}"
WARMUP_SECONDS="${WARMUP_SECONDS:-4}"
CAPTURE_TIMEOUT="${CAPTURE_TIMEOUT:-30}"

STAMP="$(date +%Y%m%d_%H%M%S)"
LOCAL_DIR="${1:-${PROJECT_ROOT}/unitree_dex3/detect_img/robot_snapshot_${STAMP}}"
REMOTE_CONTAINER_DIR="/workspaces/unitree_dex3/detect_img/robot_snapshot_${STAMP}"
REMOTE_HOST_DIR="/home/unitree/Desktop/unitree_dex3/detect_img/robot_snapshot_${STAMP}"

mkdir -p "${LOCAL_DIR}"

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
  ASKPASS_FILE="$(mktemp /tmp/robot_snapshot_askpass.XXXXXX)"
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

ssh_cmd() {
  env "${ssh_env[@]}" "${ssh_prefix[@]}" ssh -o StrictHostKeyChecking=no "${ROBOT_USER}@${ROBOT_HOST}" "$@"
}

scp_cmd() {
  env "${ssh_env[@]}" "${ssh_prefix[@]}" scp -o StrictHostKeyChecking=no "$@"
}

echo "Saving robot camera snapshot to: ${LOCAL_DIR}"

ssh_cmd "REMOTE_CONTAINER_DIR='${REMOTE_CONTAINER_DIR}' CONTAINER_NAME='${CONTAINER_NAME}' WARMUP_SECONDS='${WARMUP_SECONDS}' CAPTURE_TIMEOUT='${CAPTURE_TIMEOUT}' bash -s" <<'REMOTE'
set -euo pipefail

docker exec "${CONTAINER_NAME}" bash -lc "
set -eo pipefail
source /opt/ros/humble/setup.bash
source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash
source /workspaces/unitree_dex3/install_container/setup.bash
mkdir -p '${REMOTE_CONTAINER_DIR}'
rm -f '${REMOTE_CONTAINER_DIR}'/*.jpg
timeout '${CAPTURE_TIMEOUT}'s ros2 run unitree_g1_dex3_stack v4l2_apriltag_trigger.py \
  --ros-args \
  --params-file /workspaces/unitree_dex3/install_container/unitree_g1_dex3_stack/share/unitree_g1_dex3_stack/config/apriltag_button_press.yaml \
  -p save_raw_images:=true \
  -p debug_image_dir:='${REMOTE_CONTAINER_DIR}' \
  -p continuous_capture:=false \
  > /tmp/robot_snapshot.log 2>&1 &
node_pid=\$!
sleep '${WARMUP_SECONDS}'
ros2 topic pub --once /apriltag/capture_trigger std_msgs/msg/Empty '{}' > /tmp/robot_snapshot_trigger.log 2>&1 || true
wait \${node_pid} || true
echo SNAPSHOT_LOG
tail -80 /tmp/robot_snapshot.log || true
echo FILES
ls -l '${REMOTE_CONTAINER_DIR}' || true
"
REMOTE

scp_cmd "${ROBOT_USER}@${ROBOT_HOST}:${REMOTE_HOST_DIR}/*.jpg" "${LOCAL_DIR}/"

echo
echo "Done. Files:"
ls -lh "${LOCAL_DIR}"
