#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="${IMAGE_NAME:-unitree-dex3:humble}"
INSTALL_PINOCCHIO_PIP="${INSTALL_PINOCCHIO_PIP:-1}"
INSTALL_UNITREE_SDK2_PYTHON="${INSTALL_UNITREE_SDK2_PYTHON:-1}"
BUILD_NETWORK="${BUILD_NETWORK:-host}"
USE_PROXY="${USE_PROXY:-0}"
if [[ "${USE_PROXY}" == "1" ]]; then
  HTTP_PROXY_VALUE="${PROXY_URL:-${HTTP_PROXY:-${http_proxy:-}}}"
  HTTPS_PROXY_VALUE="${PROXY_URL:-${HTTPS_PROXY:-${https_proxy:-}}}"
  NO_PROXY_VALUE="${NO_PROXY:-${no_proxy:-localhost,127.0.0.1}}"
else
  HTTP_PROXY_VALUE=""
  HTTPS_PROXY_VALUE=""
  NO_PROXY_VALUE=""
fi
PROXY_ARGS=()
if [[ -n "${HTTP_PROXY_VALUE}" ]]; then
  PROXY_ARGS+=("--build-arg" "HTTP_PROXY=${HTTP_PROXY_VALUE}" "--build-arg" "http_proxy=${HTTP_PROXY_VALUE}")
fi
if [[ -n "${HTTPS_PROXY_VALUE}" ]]; then
  PROXY_ARGS+=("--build-arg" "HTTPS_PROXY=${HTTPS_PROXY_VALUE}" "--build-arg" "https_proxy=${HTTPS_PROXY_VALUE}")
fi
if [[ -n "${NO_PROXY_VALUE}" ]]; then
  PROXY_ARGS+=("--build-arg" "NO_PROXY=${NO_PROXY_VALUE}" "--build-arg" "no_proxy=${NO_PROXY_VALUE}")
fi

cat <<EOF
This build can download data from the network:
- Docker base image: ros:humble-ros-base-jammy
- apt packages inside the image
- pip packages inside the image
- Unitree SDK2 / Unitree ROS2 / Unitree SDK2 Python git repositories

Image: ${IMAGE_NAME}
INSTALL_PINOCCHIO_PIP=${INSTALL_PINOCCHIO_PIP}
INSTALL_UNITREE_SDK2_PYTHON=${INSTALL_UNITREE_SDK2_PYTHON}
BUILD_NETWORK=${BUILD_NETWORK}
USE_PROXY=${USE_PROXY}
HTTP_PROXY=${HTTP_PROXY_VALUE:-<not set>}
HTTPS_PROXY=${HTTPS_PROXY_VALUE:-<not set>}
EOF

read -r -p "Run docker build now? [y/N] " answer
case "${answer}" in
  y|Y|yes|YES) ;;
  *) echo "Cancelled."; exit 0 ;;
esac

docker build \
  --network="${BUILD_NETWORK}" \
  "${PROXY_ARGS[@]}" \
  --build-arg INSTALL_PINOCCHIO_PIP="${INSTALL_PINOCCHIO_PIP}" \
  --build-arg INSTALL_UNITREE_SDK2_PYTHON="${INSTALL_UNITREE_SDK2_PYTHON}" \
  -t "${IMAGE_NAME}" \
  "${SCRIPT_DIR}"
