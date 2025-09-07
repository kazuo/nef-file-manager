#!/usr/bin/env bash

set -e

if ! command -v uv &> /dev/null
then
    echo "uv not installed, please install to continue."
    echo "See https://docs.astral.sh/uv/getting-started/installation/"
    exit
fi

# Get the absolute path of the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script's directory to ensure proper context
cd "$SCRIPT_DIR"

uv run python "${SCRIPT_DIR}/nef_file_manager"
