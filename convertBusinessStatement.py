# Copy of convertStatement.py for Pinecrest business account (4577) debugging
# Original author: Julian Kingman
# Modified for business statement compatibility

import sys
import argparse
import os
import pdfplumber
import sys
import re
import csv
from dateutil.relativedelta import relativedelta
from datetime import datetime

def extract_transactions_for_page(page, columns, statement_date):
    transactions = []
    words = page.extract_words(keep_blank_chars=True)
    words.sort(key=lambda word: (word['top'], word['x0']))

    # Find all header word candidates on the page
    header_word_list = ['Date', 'Number', 'Description', 'Deposits/', 'Credits', 'Withdrawals/', 'Debits', 'Ending daily', 'balance']
    header_words = [w for w in words if any(hw in w['text'] for hw in header_word_list)]
    # If header words found, proceed as before
    if header_words:
        # Sort by x0
        header_words.sort(key=lambda w: w['x0'])
        # Merge headers by x0 proximity (within 20 units)
        merged_headers = []
        i = 0
        while i < len(header_words):
            base = header_words[i]
            merged = base['text'].strip()
            x0 = base['x0']
            # Try to merge with next word if close in x0
            if i+1 < len(header_words) and abs(header_words[i+1]['x0'] - x0) < 20:
                merged += header_words[i+1]['text'].strip()
                i += 1
            merged_headers.append({'header': merged, 'x0': x0})
            i += 1
        print(f"[DEBUG] Merged headers: {merged_headers}")
        # Map merged headers to expected columns
        col_map = {
            'Date': 'Date',
            'Number': 'Number',
            'Description': 'Description',
            'Deposits/Credits': 'Deposits/Credits',
            'Withdrawals/Debits': 'Withdrawals/Debits',
            'Ending dailybalance': 'Ending daily balance',
        }
        column_positions = {}
        for mh in merged_headers:
            col = col_map.get(mh['header'], None)
            if col:
                column_positions[col] = mh['x0']
        # Fill missing columns with None
        for col in columns:
            if col not in column_positions:
                column_positions[col] = None
        print(f"[DEBUG] Final column positions: {column_positions}")
        if None in column_positions.values():
            print(f"[WARN] Could not find all columns with word-based detection. Falling back to text extraction.")
            # Skip row-processing and proceed to fallback logic below
        else:
            # Group words by row
            rows = []
            for word in words:
                row = word['top']
                if not rows or rows[-1][0] != row:
                    rows.append((row, []))
                rows[-1][1].append(word)
            for _, words_in_row in rows:
                words_in_row.sort(key=lambda word: word['x0'])
            for i, (row, words_in_row) in enumerate(rows):
                transaction = {column: '' for column in columns}
                for word in words_in_row:
                    if 'Ending balance' in word['text']:
                        break
                    for column in columns:
                        try:
                            col_idx = columns.index(column)
                            next_col = columns[col_idx+1] if col_idx+1 < len(columns) else None
                            lower = column_positions[column]
                            upper = column_positions.get(next_col, float('inf'))
                            if lower is not None and lower <= word['x0'] < upper:
                                if column == "Date" and re.match(r'\d{1,2}/\d{1,2}', word['text']):
                                    transaction["Date"] = word['text']
                                elif column != "Date":
                                    transaction[column] += word['text'] + ' '
                        except Exception as e:
                            print(f'[ERROR] Processing word: {word}, Columns: {columns}, Positions: {column_positions}, Exception: {e}')
                            # Do not exit; continue
                if any(transaction.values()):
                    transactions.append(transaction)
            return transactions
    # Fallback: use extract_text to find header line
    # --- Split header detection and robust transaction parsing ---
    text = page.extract_text()
    if not text:
        return None
    lines = text.splitlines()
    # Look for header: line with 'Description', 'Credits', 'Debits', 'balance', previous with 'Deposits', 'Withdrawals', 'Ending daily'
    header_idx = None
    prev_keywords = ["deposits", "withdrawals", "ending daily"]
    curr_keywords = ["description", "credits", "debits", "balance"]
    import sys
    import pdfplumber
    pdf = pdfplumber.open(page.pdf.stream.name)
    header_found = False
    header_idx = None
    header_page = None
    # Always check for three-line header first on every page, regardless of merged header logic
    import re
    def norm(s):
        return re.sub(r'\s+', ' ', s.lower().replace('/', '')).strip()
    header_found = False
    header_idx = None
    header_page = None
    for page_idx, pg in enumerate(pdf.pages):
        text = pg.extract_text()
        if not text:
            continue
        lines = text.splitlines()
        # Print all normalized lines for diagnostics
        print(f"[DIAG] Normalized lines for page {page_idx}:")
        for idx, line in enumerate(lines):
            print(f"  {idx}: {norm(line)}")
        for i in range(len(lines)-2):
            l0 = norm(lines[i])
            l1 = norm(lines[i+1])
            l2 = norm(lines[i+2])
            print(f"[DEBUG] Checking lines {i}-{i+2}:\n  l0: {l0}\n  l1: {l1}\n  l2: {l2}")
            # Robust keyword checks
            l1hits = sum(k in l1 for k in ["deposits", "withdrawals"]) + ("ending" in l1 and "daily" in l1)
            l2hits = sum(k in l2 for k in ["date", "number", "description", "credits", "debits", "balance"])
            if (
                'transaction history' in l0 and
                l1hits >= 2 and
                l2hits >= 4
            ):
                print(f"[DEBUG] Three-line header matched at lines {i}-{i+2} on page {page_idx}")
                header_found = True
                header_idx = i+2
                header_page = page_idx
                break
        if header_found:
            break
    # Remove merged/two-line header logic: always rely on robust three-line header fallback
    if not header_found:
        print("[ERROR] Could not find business transaction header in any page.")
        return []
    # Parse transactions with improved logic
    lines = pdf.pages[header_page].extract_text().splitlines()
    transactions = []
    csv_fieldnames = ["Date", "Number", "Description", "Deposits/Credits", "Withdrawals/Debits", "Ending daily balance"]
    current = None
    
    def clean_amount(amount_str):
        """Clean amount string and return float, or empty string if invalid."""
        if not amount_str or amount_str.strip() == '':
            return ''
        cleaned = amount_str.replace(',', '').replace('$', '').strip()
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return ''
    
    def is_amount(text):
        """Check if text looks like a monetary amount (not a reference number)."""
        if not text:
            return False
        cleaned = text.replace(',', '').replace('$', '').strip()
        
        try:
            value = float(cleaned)
            
            # Rule out obvious non-monetary numbers:
            # 1. Very large numbers (likely reference/transaction IDs)
            if value > 100000:  # > $100K is likely a reference number (lowered threshold)
                return False
            
            # 2. Numbers that look like dates (YYMMDD format)
            if len(cleaned) == 6 and cleaned.isdigit():
                # Check if it could be a date (YYMMDD)
                yy = int(cleaned[:2])
                mm = int(cleaned[2:4])
                dd = int(cleaned[4:6])
                if 20 <= yy <= 30 and 1 <= mm <= 12 and 1 <= dd <= 31:
                    return False
            
            # 3. Numbers that look like transaction IDs (very long integers)
            if len(cleaned) > 6 and cleaned.isdigit():
                return False
                
            # 4. Must have reasonable decimal places for currency
            if '.' in cleaned:
                decimal_part = cleaned.split('.')[1]
                if len(decimal_part) > 2:  # More than 2 decimal places is suspicious
                    return False
            
            # 5. Card numbers and reference codes (contain letters and numbers)
            if re.search(r'[a-zA-Z]', cleaned):
                return False
            
            return True
        except ValueError:
            return False
    
    # Process all lines after header, building complete transactions
    i = header_idx + 1
    while i < len(lines):
        line = lines[i]
        
        if "ending balance" in line.lower() or "totals" in line.lower():
            break
        
        parts = line.split()
        if not parts:
            i += 1
            continue
            
        # Heuristic: a new transaction starts with a date (MM/DD or M/D)
        if len(parts) >= 2 and re.match(r'\d{1,2}/\d{1,2}', parts[0]):
            # Save previous transaction
            if current:
                transactions.append(current)
            
            # Start new transaction
            current = {col: '' for col in csv_fieldnames}
            current["Date"] = parts[0]
            
            # Collect the main transaction line and any continuation lines
            transaction_text = line
            j = i + 1
            
            # Look ahead for continuation lines (lines that don't start with dates)
            while j < len(lines):
                next_line = lines[j]
                next_parts = next_line.split()
                
                # Stop if we hit another transaction (starts with date) or end markers
                if (next_parts and re.match(r'\d{1,2}/\d{1,2}', next_parts[0])) or \
                   "ending balance" in next_line.lower() or "totals" in next_line.lower() or \
                   not next_line.strip():
                    break
                
                # This is a continuation line - add it to the transaction
                transaction_text += ' ' + next_line.strip()
                j += 1
            
            # Parse the complete transaction text
            complete_parts = transaction_text.split()
            current["Date"] = complete_parts[0]
            
            # Find all numeric values that could be amounts
            numeric_values = []
            description_parts = []
            
            for i, part in enumerate(complete_parts[1:], 1):  # Skip date
                # Check if this looks like a monetary amount
                cleaned_part = part.replace(',', '').replace('$', '')
                if re.match(r'^\d+\.\d{2}$', cleaned_part):  # Exact format: digits.XX
                    try:
                        value = float(cleaned_part)
                        numeric_values.append((i, part, value))
                    except ValueError:
                        description_parts.append(part)
                elif re.match(r'^\d+$', cleaned_part) and len(cleaned_part) <= 6:  # Whole dollars, reasonable length
                    try:
                        value = float(cleaned_part)
                        if value <= 50000:  # Reasonable transaction limit
                            numeric_values.append((i, part, value))
                        else:
                            description_parts.append(part)  # Likely reference number
                    except ValueError:
                        description_parts.append(part)
                else:
                    description_parts.append(part)
            
            # Build description from non-numeric parts
            current["Description"] = ' '.join(description_parts)
            
            # Initialize variables
            transaction_amount = None
            ending_balance = None
            
            # Assign amounts based on Wells Fargo format
            if len(numeric_values) == 2:
                # Two amounts: transaction amount and ending balance
                # The smaller amount is usually the transaction, larger is balance
                first_idx, first_str, first_val = numeric_values[0]
                second_idx, second_str, second_val = numeric_values[1]
                
                if first_val < second_val:
                    # First amount is transaction, second is balance
                    transaction_amount = first_str
                    ending_balance = second_str
                else:
                    # Second amount is transaction, first might be balance or reference
                    transaction_amount = second_str
                    if first_val > 100:  # Reasonable balance minimum
                        ending_balance = first_str
                        
            elif len(numeric_values) == 1:
                # Single amount - this is the transaction amount
                transaction_amount = numeric_values[0][1]
                
            # Assign transaction amount to correct column based on transaction type
            if transaction_amount:
                desc_lower = current["Description"].lower()
                deposit_keywords = ['transfer from', 'deposit', 'credit', 'payroll', 'income', 'matterfi', 'refund']
                
                is_deposit = any(kw in desc_lower for kw in deposit_keywords)
                
                if is_deposit:
                    current["Deposits/Credits"] = clean_amount(transaction_amount)
                    current["Withdrawals/Debits"] = ''
                else:
                    # Default to withdrawal for most transactions (purchases, payments, etc.)
                    current["Deposits/Credits"] = ''
                    current["Withdrawals/Debits"] = clean_amount(transaction_amount)
            
            # Set ending balance if found
            if ending_balance:
                current["Ending daily balance"] = clean_amount(ending_balance)

            # Extract transaction number/type if available (usually second part)
            if len(complete_parts) > 1 and not is_amount(complete_parts[1]):
                current["Number"] = complete_parts[1]
            
            # Skip to the next unprocessed line
            i = j
        else:
            # Skip lines that don't start transactions (handled above in multi-line logic)
            i += 1
    
    # Add final transaction
    if current:
        transactions.append(current)
    
    return transactions

def convert_pdf(pdf_path, year=None):
    import pdfplumber
    import os
    import re
    
    # Extract year from folder path if not provided
    if year is None:
        # Look for year in the full path (e.g., 2023_statements_4577 or 2024_statements_4577)
        year_match = re.search(r'(202[34])_statements', pdf_path)
        if year_match:
            year = year_match.group(1)
        else:
            raise ValueError(f"Could not extract year from path: {pdf_path}. Expected folder format like '2023_statements_4577' or '2024_statements_4577'")
    
    print(f"[INFO] Using year {year} for transactions in {os.path.basename(pdf_path)}")
    
    pdf = pdfplumber.open(pdf_path)
    columns = ["Date", "Number", "Description", "Deposits/Credits", "Withdrawals/Debits", "Ending daily balance"]
    all_transactions = []
    header_found = False
    seen_transactions = set()  # Track unique transactions to avoid duplicates
    
    for i, page in enumerate(pdf.pages):
        transactions = extract_transactions_for_page(page, columns, None)
        if transactions:
            if not header_found:
                print(f"[DEBUG] Found headers on page {i}")
                header_found = True
            
            # Deduplicate transactions at the page level
            unique_transactions = []
            duplicates_found = 0
            
            for transaction in transactions:
                # Add year to date field if it's in MM/DD format
                if 'Date' in transaction and transaction['Date'] and re.match(r'\d{1,2}/\d{1,2}', transaction['Date']):
                    # Format as MM/DD/YYYY to match bank's downloaded format
                    transaction['Date'] = f"{transaction['Date']}/{year}"
                
                # Create a unique signature for each transaction
                signature = f"{transaction['Date']}|{transaction['Description']}|{transaction.get('Deposits/Credits', '')}|{transaction.get('Withdrawals/Debits', '')}"
                
                if signature not in seen_transactions:
                    seen_transactions.add(signature)
                    unique_transactions.append(transaction)
                else:
                    duplicates_found += 1
            
            print(f"[DEBUG] Page {i}: {len(transactions)} raw transactions, {len(unique_transactions)} unique, {duplicates_found} duplicates skipped")
            all_transactions.extend(unique_transactions)
    
    if not header_found:
        print("[ERROR] Could not find transaction headers on any page.")
        return
    csv_file = pdf_path.replace('.pdf', '_transactions.csv')
    with open(csv_file, 'w', newline='') as csvfile:
        # Use quoting=csv.QUOTE_ALL to quote all fields like the bank's downloaded CSV
        writer = csv.DictWriter(csvfile, fieldnames=columns, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for t in all_transactions:
            writer.writerow(t)
    print(f"[SUCCESS] CSV file created: {csv_file}")

def batch_convert(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                print(f"[BATCH] Converting {pdf_path}")
                convert_pdf(pdf_path)  # Year will be auto-extracted from path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert Pinecrest business statement PDF(s) to CSV')
    parser.add_argument('--batch', action='store_true', help='Convert all PDFs in the specified directory')
    parser.add_argument('--year', type=str, help='Year to use for transactions (e.g., 2023, 2024)')
    parser.add_argument('path', type=str, help='PDF file or directory to convert')
    args = parser.parse_args()

    if args.batch:
        batch_convert(args.path)
    else:
        convert_pdf(args.path, args.year)
