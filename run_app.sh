#!/bin/bash

echo "========================================"
echo "   Krishi-Gati - Farmer Market Advisor"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed!"
    echo "Please install Python from https://python.org"
    exit 1
fi

# Check if requirements are installed
echo "Checking dependencies..."
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "Installing required packages..."
    pip3 install -r requirements.txt
fi

echo ""
echo "Starting Krishi-Gati..."
echo "Opening browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run app.py --server.port 8501
