#!/bin/bash
# =============================================================================
# HTML to PDF Converter for CV Agent
# Uses WeasyPrint to convert HTML CV to PDF
# =============================================================================
#
# Usage:
#   ./html_to_pdf.sh <input.html> [output.pdf]
#
# Examples:
#   ./html_to_pdf.sh cv.html
#   ./html_to_pdf.sh cv.html cv_output.pdf
#   ./html_to_pdf.sh ../applications/06-01-25_google_security-engineer/output/cv.html
#
# Requirements:
#   - weasyprint (pip install weasyprint)
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print error and exit
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

# Function to print warning
warn() {
    echo -e "${YELLOW}Warning: $1${NC}" >&2
}

# Function to print success
success() {
    echo -e "${GREEN}$1${NC}"
}

# Check if weasyprint is installed
if ! command -v weasyprint &> /dev/null; then
    error_exit "weasyprint is not installed. Install with: pip install weasyprint"
fi

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input.html> [output.pdf]"
    echo ""
    echo "Examples:"
    echo "  $0 cv.html                    # Output: cv.pdf"
    echo "  $0 cv.html my_cv.pdf          # Output: my_cv.pdf"
    exit 1
fi

INPUT_FILE="$1"

# Verify input file exists
if [ ! -f "$INPUT_FILE" ]; then
    error_exit "Input file not found: $INPUT_FILE"
fi

# Determine output file
if [ $# -ge 2 ]; then
    OUTPUT_FILE="$2"
else
    # Replace .html with .pdf
    OUTPUT_FILE="${INPUT_FILE%.html}.pdf"
fi

# Get absolute paths for clarity
INPUT_ABS=$(readlink -f "$INPUT_FILE" 2>/dev/null || echo "$INPUT_FILE")
OUTPUT_ABS=$(readlink -f "$OUTPUT_FILE" 2>/dev/null || echo "$OUTPUT_FILE")

echo "Converting HTML to PDF..."
echo "  Input:  $INPUT_ABS"
echo "  Output: $OUTPUT_ABS"

# Run weasyprint
if weasyprint "$INPUT_FILE" "$OUTPUT_FILE" 2>&1; then
    success "PDF generated successfully: $OUTPUT_FILE"

    # Show file size
    if [ -f "$OUTPUT_FILE" ]; then
        SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
        echo "  Size: $SIZE"
    fi
else
    error_exit "weasyprint failed to generate PDF"
fi
