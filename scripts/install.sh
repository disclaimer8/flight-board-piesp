#!/usr/bin/env bash
#
# Build hzeller/rpi-rgb-led-matrix + its Python bindings on a Raspberry Pi,
# then install this project into a venv. Run ON THE PI (armv6l/armv7l), not in
# CI — the matrix library compiles native code against the Pi's GPIO.
#
#   ./scripts/install.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MATRIX_DIR="${HOME}/rpi-rgb-led-matrix"

echo ">> Installing build dependencies (apt)…"
sudo apt-get update
sudo apt-get install -y git build-essential python3-dev python3-venv python3-pip cython3

echo ">> Cloning/updating hzeller/rpi-rgb-led-matrix…"
if [ -d "${MATRIX_DIR}/.git" ]; then
    git -C "${MATRIX_DIR}" pull --ff-only
else
    git clone https://github.com/hzeller/rpi-rgb-led-matrix.git "${MATRIX_DIR}"
fi

echo ">> Building the C++ library and Python bindings…"
make -C "${MATRIX_DIR}" build-python PYTHON="$(command -v python3)"

echo ">> Creating project venv (with system site-packages for rgbmatrix)…"
python3 -m venv --system-site-packages "${REPO_ROOT}/.venv"
# shellcheck disable=SC1091
source "${REPO_ROOT}/.venv/bin/activate"
pip install --upgrade pip

echo ">> Installing rgbmatrix Python binding into the venv…"
sudo make -C "${MATRIX_DIR}" install-python PYTHON="$(command -v python3)"

echo ">> Installing flight-board…"
pip install -e "${REPO_ROOT}"

echo
echo ">> Done. Next steps:"
echo "   cp ${REPO_ROOT}/config.example.yaml ${REPO_ROOT}/config.yaml   # then edit"
echo "   sudo cp ${REPO_ROOT}/systemd/flight-board.service /etc/systemd/system/"
echo "   sudo systemctl enable --now flight-board"
