#!/bin/bash

# -----------------------------------------------------------------------------
# JARVIS V3 Build Script for Ubuntu (Linux)
# 
# This script:
#   - Verifies the virtual environment is active and all dependencies are installed.
#   - Checks for required tools (Python, PyInstaller, etc.).
#   - Builds a standalone executable using PyInstaller.
#   - Installs the executable and a .desktop file (optional).
#   - Logs all actions to a build log file.
# -----------------------------------------------------------------------------

set -euo pipefail  # strict mode

# ----------------------------------------
# Configuration
# ----------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BUILD_LOG="$PROJECT_ROOT/build.log"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
SPEC_FILE="$PROJECT_ROOT/JARVIS.spec"  # optional, we generate dynamically
APP_NAME="JARVIS"
ICON_FILE=""  # set to e.g., "src/static/icon.ico" if available

# Flags
INSTALL_DESKTOP="${INSTALL_DESKTOP:-1}"  # set to 0 to skip desktop file installation
CONSOLE_MODE="${CONSOLE_MODE:-0}"        # set to 1 to build with console (for debugging)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ----------------------------------------
# Helper Functions
# ----------------------------------------
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo -e "$msg" | tee -a "$BUILD_LOG"
}

log_success() {
    log "${GREEN}✓ $*${NC}"
}

log_error() {
    log "${RED}✗ $*${NC}" >&2
    exit 1
}

log_warning() {
    log "${YELLOW}⚠ $*${NC}"
}

log_info() {
    log "${BLUE}➜ $*${NC}"
}

# Check if a command is available
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Command '$1' not found. Please install it and try again."
    fi
}

# Check if Python package is installed
check_python_package() {
    python3 -c "import $1" 2>/dev/null || {
        log_error "Python package '$1' is not installed. Run: pip install $1"
    }
}

# ----------------------------------------
# Start of build process
# ----------------------------------------
log_info "============================================"
log_info "  JARVIS V3 Build Process"
log_info "============================================"

# Ensure we are in the project root
cd "$PROJECT_ROOT"

# 1. Check environment
log_info "Checking environment..."

# Python version
check_command python3
PYTHON_VERSION=$(python3 --version)
log_info "Using $PYTHON_VERSION"

# Virtual environment
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    log_warning "No active virtual environment detected."
    log_warning "It's recommended to use a venv. Continuing anyway..."
else
    log_success "Virtual environment active: $VIRTUAL_ENV"
fi

# Required tools
check_command pip
check_command python3
if ! command -v pyinstaller &> /dev/null; then
    log_info "PyInstaller not found. Installing..."
    pip install pyinstaller
fi
check_command pyinstaller

# Check required Python packages
log_info "Checking Python dependencies..."
REQUIRED_PACKAGES=("PyQt6" "pydantic" "requests" "psutil" "llama_cpp")
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    check_python_package "$pkg"
done
log_success "All required packages are installed."

# 2. Clean previous builds (optional)
log_info "Cleaning previous build artifacts..."
rm -rf "$BUILD_DIR" "$DIST_DIR" "$SPEC_FILE" 2>/dev/null || true
log_success "Cleanup complete."

# 3. Ensure required directories and files exist
log_info "Checking project files..."
if [[ ! -d "src" ]]; then
    log_error "src/ directory not found. Are you in the project root?"
fi
if [[ ! -f "src/main.py" ]]; then
    log_error "src/main.py not found. Please ensure it exists."
fi
# Optionally check for models (they might be downloaded later)
if [[ ! -d "models" ]]; then
    log_warning "models/ directory not found. The model will be downloaded at runtime if needed."
fi

# 4. Build with PyInstaller
log_info "Building executable with PyInstaller..."

# Determine windowed flag
WINDOWED_FLAG="--windowed"
if [[ "$CONSOLE_MODE" -eq 1 ]]; then
    WINDOWED_FLAG="--console"
    log_warning "Building with console mode (for debugging)."
fi

# Build command
PYINSTALLER_CMD=(
    python3 -m PyInstaller
    --onefile
    $WINDOWED_FLAG
    --name "$APP_NAME"
    --add-data "src/static:src/static"
    --add-data "src:src"
    --add-data "models:models"
    --add-data ".env:."
    --add-data "config:config"  # if you have a config folder
    --add-data "data:data"      # if you need data folder at runtime
    --distpath "$DIST_DIR"
    --workpath "$BUILD_DIR"
    --specpath "$PROJECT_ROOT"
    --clean
    src/main.py
)

# Add icon if present
if [[ -n "$ICON_FILE" && -f "$ICON_FILE" ]]; then
    PYINSTALLER_CMD+=(--icon "$ICON_FILE")
fi

# Execute the build
log_info "Running: ${PYINSTALLER_CMD[*]}"
if "${PYINSTALLER_CMD[@]}" >> "$BUILD_LOG" 2>&1; then
    log_success "Build completed successfully."
else
    log_error "PyInstaller build failed. Check $BUILD_LOG for details."
fi

# Verify output
EXECUTABLE="$DIST_DIR/$APP_NAME"
if [[ ! -f "$EXECUTABLE" ]]; then
    log_error "Build failed: executable not found at $EXECUTABLE"
fi
log_success "Executable created: $EXECUTABLE"

# 5. Install (optional)
if [[ "$INSTALL_DESKTOP" -eq 1 ]]; then
    log_info "Installing executable and desktop entry..."

    # Copy executable to /usr/local/bin
    sudo cp "$EXECUTABLE" /usr/local/bin/ || {
        log_warning "Could not copy to /usr/local/bin. Skipping system installation."
        INSTALL_DESKTOP=0
    }

    if [[ "$INSTALL_DESKTOP" -eq 1 ]]; then
        # Create .desktop file dynamically with absolute path
        DESKTOP_FILE="$PROJECT_ROOT/$APP_NAME.desktop"
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=JARVIS V3 - Phoenix Intelligence Platform
Exec=/usr/local/bin/$APP_NAME
Icon=$PROJECT_ROOT/src/static/icon.png
Terminal=false
Categories=Utility;Development;
StartupNotify=true
EOF

        # Install desktop file
        sudo cp "$DESKTOP_FILE" /usr/share/applications/ || {
            log_warning "Could not install desktop file. Ensure /usr/share/applications/ is writable."
        }

        # Update desktop database (optional)
        if command -v update-desktop-database &> /dev/null; then
            sudo update-desktop-database
            log_success "Desktop database updated."
        fi
        log_success "Desktop entry installed."
    fi
fi

# 6. Final summary
log_info "============================================"
log_success "Build and installation complete."
log_info "Executable: $EXECUTABLE"
if [[ "$INSTALL_DESKTOP" -eq 1 && -f "/usr/share/applications/$APP_NAME.desktop" ]]; then
    log_info "You can launch JARVIS from your application menu."
else
    log_info "You can run the executable manually: $EXECUTABLE"
fi
log_info "Build log: $BUILD_LOG"
log_info "============================================"

exit 0
