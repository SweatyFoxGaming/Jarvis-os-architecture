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
