#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Building JARVIS for Ubuntu ---"

# Check if we are in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Error: Virtual environment not active. Run 'source venv/bin/activate' first."
    exit 1
fi

# Ensure PYTHONPATH includes src
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Build the executable
echo "Starting PyInstaller build..."
# We use --collect-all for libraries that might have dynamic data
python3 -m PyInstaller --onefile --windowed \
    --name "JARVIS" \
    --add-data "src:src" \
    --add-data "models:models" \
    src/main.py

if [ ! -f "dist/JARVIS" ]; then
    echo "Error: Build failed. dist/JARVIS not found."
    exit 1
fi

echo "Build complete. Executable located in dist/JARVIS"

echo "--- Installing Desktop Entry ---"
sudo cp dist/JARVIS /usr/local/bin/
sudo cp JARVIS.desktop /usr/share/applications/
sudo chmod +x /usr/share/applications/JARVIS.desktop

echo "Installation complete. You can now find JARVIS in your application menu."
