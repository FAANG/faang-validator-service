import json
import sys
import json
import gspread
import os
from typing import List, Dict, Any, Optional


def process_headers(headers: List[str]) -> List[str]:
    """Process headers according to the rules for duplicates."""
    new_headers = []
    i = 0
    while i < len(headers):
        h = headers[i]

        # Case 1: Header contains a period (.)
        if '.' in h and new_headers:
            # Concatenate with the previous header name
            prev_header = new_headers[-1]
            new_header = h.split('.')[0]
            new_headers.append(f"{prev_header} {new_header}")
            # Case 2: Consecutive duplicates
        elif i + 1 < len(headers) and headers[i + 1] == h:
            new_headers.append(h)
            while i + 1 < len(headers) and headers[i + 1] == h:
                i += 1
                new_headers.append(h)
        else:
            # Case 3: Non-consecutive duplicate
            if h in new_headers:
                # Concatenate with the last header name
                last_header = new_headers[-1] if new_headers else ""
                new_headers.append(f"{last_header}_{h}")
            else:
                new_headers.append(h)
        i += 1
    return new_headers


class GoogleSheetProcessor:
    def __init__(self, spreadsheet_id: str, project: Optional[str] = None):
        self.spreadsheet_id = spreadsheet_id
        self.project = project

    def process_spreadsheet(self, number) -> list[dict[str, Any]]:
        """Main method to process the spreadsheet and return JSON data."""
        try:
            # Create a client with optional project name for authentication
            if self.project:
                # Use the specified project for authentication
                client = gspread.service_account(None, project=self.project)
            else:
                # Use default authentication (for backward compatibility)
                client = gspread.service_account(None)

            # Open spreadsheet and get worksheet by index
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.get_worksheet(number)

            # Get all values
            data = worksheet.get_all_values()
            if not data:
                raise ValueError("No data found in the spreadsheet")

            headers = data[0]
            rows = data[1:]

            # Process headers and build JSON
            processed_headers = process_headers(headers)
            grouped_data = build_json_data(processed_headers, rows)

            return grouped_data

        except Exception as e:
            raise Exception(f"Error processing spreadsheet: {str(e)}")

from typing import List, Dict, Any

def build_json_data(headers: List[str], rows: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Build JSON structure from processed headers and rows.
    Only include 'Health Status' if it exists in the headers.
    """
    grouped_data = []
    has_health_status = any(h.startswith("Health Status") for h in headers)

    for row in rows:
        record: Dict[str, Any] = {}
        if has_health_status:
            record["Health Status"] = []

        i = 0
        while i < len(headers):
            col = headers[i]
            val = row[i] if i < len(row) else ""

            # ✅ Special handling if Health Status is in headers
            if has_health_status and col.startswith("Health Status"):
                # Check next column for Term Source ID
                if i + 1 < len(headers) and "Term Source ID" in headers[i + 1]:
                    term_val = row[i + 1] if i + 1 < len(row) else ""

                    record["Health Status"].append({
                        "text": val,
                        "term": term_val
                    })
                    i += 2
                else:
                    if val:
                        record["Health Status"].append({
                            "text": val.strip(),
                            "term": ""
                        })
                    i += 1
                continue

            # ✅ Normal processing for all other columns
            if col in record:
                if not isinstance(record[col], list):
                    record[col] = [record[col]]
                record[col].append(val)
            else:
                record[col] = val
            i += 1

        grouped_data.append(record)

    return grouped_data
