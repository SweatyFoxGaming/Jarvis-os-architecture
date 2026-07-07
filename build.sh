#!/bin/bash
echo "--- Building JARVIS for Ubuntu ---"
# Ensure we are in the project root
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Build the executable
# --onefile: single executable
# --windowed: no terminal window on start (since we have a GUI)
# --add-data: include memory and documentation templates
pyinstaller --onefile --windowed \
    --name "JARVIS" \
    --add-data "src:src" \
    src/main.py

echo "Build complete. Executable located in dist/JARVIS"

echo "--- Installing Desktop Entry ---"
sudo cp dist/JARVIS /usr/local/bin/
sudo cp JARVIS.desktop /usr/share/applications/
sudo chmod +x /usr/share/applications/JARVIS.desktop

echo "Installation complete. You can now find JARVIS in your application menu."
