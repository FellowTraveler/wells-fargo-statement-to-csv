# Wells Fargo Statement Extractor
Do you have PDF statements, but want to do something useful for them? Never fear, statement extractor is here!
Things you need:
 - Python
 - pdfplumber (installed via pip or something)
 - Run `python convertStatement.py "011516 WellsFargo.pdf"`
You will receive a shiny new CSV file with its beautiful contents.

## About convertBusinessStatement.py
This script is a specialized version of the Wells Fargo statement converter, specifically designed for business account statements (originally created for debugging Pinecrest business account 4577). It extracts transaction data from Wells Fargo business statement PDFs and converts them to CSV format.

### Key Features:
- Extracts transactions with Date, Number, Description, Deposits/Credits, Withdrawals/Debits, and Ending daily balance
- Handles both single PDF files and batch processing of multiple PDFs
- Auto-detects statement dates and years from PDF content or file paths
- Outputs CSV files with the same name as the input PDF

## Setup Instructions

### Prerequisites
1. **Python 3.x** installed
2. **uv** package manager (recommended for dependency management)

### Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd wells-fargo-statement-to-csv

# Create and activate virtual environment using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv add pdfplumber pandas python-dateutil
```

## Usage

### Convert a Single PDF
```bash
python convertBusinessStatement.py "path/to/statement.pdf"
```

### Convert with Specific Year
```bash
python convertBusinessStatement.py --year 2024 "path/to/statement.pdf"
```

### Batch Convert All PDFs in a Directory
```bash
python convertBusinessStatement.py --batch "path/to/statements/directory"
```

## Command Line Options
- `path`: PDF file or directory to convert (required)
- `--batch`: Convert all PDFs in the specified directory
- `--year`: Specify year for transactions (e.g., 2023, 2024) - optional, auto-detected if not provided

## Output
The script creates CSV files with the same name as the input PDF files, containing extracted transaction data with columns:
- Date
- Number
- Description
- Deposits/Credits
- Withdrawals/Debits
- Ending daily balance

**Note**: This is specifically designed for Wells Fargo **business statements** and may not work correctly with personal account statements (use `convertStatement.py` for those).

## Combine CSVs
This will combine multiple statements in a directory (recursively).
Things you need:
 - pandas (pip install pandas)
 - Run `python combineCSVByDate.py my-converted-csv-folder`

Note: csvs get overwritten without warning, so if you modify a csv, don't overwrite it!

This took a lot of trial and error and pain, profit from my suffering!
