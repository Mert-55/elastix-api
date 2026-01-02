#!/usr/bin/env python
"""
CSV Transaction Import Script

Imports transaction data from CSV files into the ElastiCom API.

Usage:
    python import_transactions.py data/data.csv
    python import_transactions.py data/data.csv --batch-size 100
    python import_transactions.py data/data.csv --url http://localhost:8000
    python import_transactions.py data/data.csv --limit 1000
"""
import argparse
import csv
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

import httpx


def parse_date(date_str: str) -> str:
    """
    Parse CSV date string to ISO format.
    
    Args:
        date_str: Date string in format "M/D/YYYY H:MM"
        
    Returns:
        ISO formatted datetime string
    """
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        return dt.isoformat()
    except ValueError:
        # Try alternative format
        dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M")
        return dt.isoformat()


def normalize_price(price_str: str) -> str:
    """
    Normalize price to 2 decimal places.
    
    Prices with more than 2 decimal places are rounded.
    Very small prices (< 0.01) are set to 0.01.
    Negative prices are converted to absolute values.
    
    Args:
        price_str: Price as string
        
    Returns:
        Normalized price string with max 2 decimal places
    """
    price = Decimal(price_str)
    
    # Convert negative prices to positive (absolute value)
    price = abs(price)
    
    # Round to 2 decimal places
    price = price.quantize(Decimal('0.01'))
    
    # Ensure minimum price of 0.01 if not zero
    if Decimal('0') < price < Decimal('0.01'):
        price = Decimal('0.01')
    
    return str(price)


def csv_row_to_transaction(row: Dict[str, str]) -> Dict[str, Any]:
    """
    Convert CSV row to transaction schema.
    
    Args:
        row: Dictionary with CSV column headers as keys
        
    Returns:
        Transaction dictionary ready for API
    """
    # Truncate fields to maximum allowed length
    invoice_no = row["InvoiceNo"][:20] if row.get("InvoiceNo") else ""
    stock_code = row["StockCode"][:20] if row.get("StockCode") else ""
    description = row.get("Description", "")[:256] if row.get("Description") else None
    customer_id = row.get("CustomerID", "")[:20] if row.get("CustomerID") else None
    country = row.get("Country", "")[:64] if row.get("Country") else None
    
    return {
        "invoice_no": invoice_no,
        "stock_code": stock_code,
        "description": description,
        "quantity": int(row["Quantity"]),
        "invoice_date": parse_date(row["InvoiceDate"]),
        "unit_price": normalize_price(row["UnitPrice"]),
        "customer_id": customer_id,
        "country": country,
    }


def read_csv_transactions(file_path: Path, limit: int = None) -> List[Dict[str, Any]]:
    """
    Read transactions from CSV file.
    
    Args:
        file_path: Path to CSV file
        limit: Optional limit on number of rows to read
        
    Returns:
        List of transaction dictionaries
    """
    transactions = []
    
    # Try different encodings
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    file_content = None
    used_encoding = None
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                file_content = f.read()
                used_encoding = encoding
                break
        except UnicodeDecodeError:
            continue
    
    if file_content is None:
        raise ValueError(f"Could not decode file with any of the supported encodings: {encodings}")
    
    # Parse CSV from string content
    from io import StringIO
    reader = csv.DictReader(StringIO(file_content))
    
    for i, row in enumerate(reader):
        if limit and i >= limit:
            break
        try:
            transaction = csv_row_to_transaction(row)
            transactions.append(transaction)
        except (ValueError, KeyError) as e:
            print(f"⚠️  Skipping row {i+2}: {e}", file=sys.stderr)
            continue
    
    return transactions


def send_batch(
    transactions: List[Dict[str, Any]],
    api_url: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Send batch of transactions to API.
    
    Args:
        transactions: List of transaction dictionaries
        api_url: Base API URL
        timeout: Request timeout in seconds
        
    Returns:
        API response dictionary
        
    Raises:
        httpx.HTTPError: If API request fails
    """
    endpoint = f"{api_url}/transactions/batch"
    payload = {"transactions": transactions}
    
    with httpx.Client(timeout=timeout) as client:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Import transactions from CSV to ElastiCom API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s data/data.csv
  %(prog)s data/data.csv --batch-size 500
  %(prog)s data/data.csv --limit 1000 --url http://localhost:8000
  %(prog)s data/data.csv --batch-size 100 --timeout 60
        """
    )
    
    parser.add_argument(
        "csv_file",
        type=Path,
        help="Path to CSV file with transaction data"
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base API URL (default: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of transactions per batch request (default: 1000)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of rows to import (default: all)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    
    args = parser.parse_args()
    
    # Validate CSV file
    if not args.csv_file.exists():
        print(f"❌ Error: File not found: {args.csv_file}", file=sys.stderr)
        sys.exit(1)
    
    if not args.csv_file.is_file():
        print(f"❌ Error: Not a file: {args.csv_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"📂 Reading transactions from {args.csv_file}")
    
    # Read CSV
    try:
        transactions = read_csv_transactions(args.csv_file, args.limit)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not transactions:
        print("⚠️  No valid transactions found in CSV", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ Loaded {len(transactions)} transaction(s)")
    
    # Send in batches
    total_created = 0
    batch_size = args.batch_size
    num_batches = (len(transactions) + batch_size - 1) // batch_size
    
    print(f"📤 Sending {num_batches} batch(es) to {args.url}")
    
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        try:
            print(f"   Batch {batch_num}/{num_batches}: {len(batch)} transactions...", end=" ")
            response = send_batch(batch, args.url, args.timeout)
            created = response.get("created", 0)
            total_created += created
            print(f"✅ {created} created")
        except httpx.HTTPError as e:
            print(f"❌ Failed", file=sys.stderr)
            print(f"   Error: {e}", file=sys.stderr)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"   API Response: {error_detail}", file=sys.stderr)
                except Exception:
                    print(f"   API Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Failed", file=sys.stderr)
            print(f"   Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)
    
    print(f"\n🎉 Import complete! Created {total_created} transaction(s)")


if __name__ == "__main__":
    main()
