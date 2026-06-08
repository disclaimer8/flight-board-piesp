#!/usr/bin/env bash
#
# Build hzeller/rpi-rgb-led-matrix's Python binding on a Raspberry Pi and
# install this project into a venv. Run ON THE PI (armv6l/armv7l), not in CI —
# the matrix library compiles native code against the Pi's GPIO.
#
# NOTE: upstream moved the Python binding build to scikit-build-core + cmake.
# The old `make build-python` / `make install-python` targets are gone, so we
# build and install the binding with pip instead. The HUB75 hardware mapping
# (adafruit-hat, regular, …) is now a *runtime* option set in config.yaml, so
# there is nothing to choose at compile time.
#
#   ./scripts/install.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MATRIX_DIR="${HOME}/rpi-rgb-led-matrix"

echo ">> Installing build dependencies (apt)…"
sudo apt-get update
sudo apt-get install -y git build-essential python3-dev python3-venv python3-pip \
    cython3 cmake ninja-build python3-pillow

echo ">> Cloning/updating hzeller/rpi-rgb-led-matrix…"
if [ -d "${MATRIX_DIR}/.git" ]; then
    git -C "${MATRIX_DIR}" pull --ff-only
else
    git clone https://github.com/hzeller/rpi-rgb-led-matrix.git "${MATRIX_DIR}"
fi

echo ">> Creating project venv (system site-packages for the system Pillow)…"
python3 -m venv --system-site-packages "${REPO_ROOT}/.venv"
# shellcheck disable=SC1091
source "${REPO_ROOT}/.venv/bin/activate"
python -m pip install --upgrade pip

echo ">> Building + installing the rgbmatrix Python binding (scikit-build-core)…"
# Install the build backend into the venv and disable build isolation so the
# build uses the system cmake/ninja (pip has no cmake/ninja wheels for armv6l).
pip install scikit-build-core cython
pip install "${MATRIX_DIR}" --no-build-isolation

echo ">> Installing flight-board…"
pip install -e "${REPO_ROOT}"

echo ">> Verifying imports…"
python -c "import rgbmatrix; print('rgbmatrix OK:', rgbmatrix.__file__)"
python -c "import flight_board; print('flight_board OK')"

echo
echo ">> Done. Next steps:"
echo "   cp ${REPO_ROOT}/config.example.yaml ${REPO_ROOT}/config.yaml   # then edit lat/lon"
echo "   sudo cp ${REPO_ROOT}/systemd/flight-board.service /etc/systemd/system/"
echo "   # adjust the paths/User in the unit if your clone is elsewhere, then:"
echo "   sudo systemctl enable --now flight-board"
