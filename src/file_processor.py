import base64
import io
import json
import re
import unicodedata
import pandas as pd
from src.google_sheet_processor import process_headers, build_json_data

def parse_contents(contents, filename):
    """
    Parse the contents of an uploaded file and convert it to a structured format.

    Args:
        contents (str): The base64-encoded contents of the file
        filename (str): The name of the uploaded file

    Returns:
        tuple: (records, sheet_name, error_message)
            - records: List of dictionaries containing the parsed data
            - sheet_name: Name of the sheet from which data was extracted
            - error_message: Error message if any, None otherwise
    """
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    sheet_name = "Sheet 1"  # Default sheet name

    try:
        if 'csv' in filename:
            # Assume you have a header row
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename or 'xlsx' in filename:
            # For Excel files, try to get the actual sheet name
            excel_file = pd.ExcelFile(io.BytesIO(decoded),engine="openpyxl")

            sheet_name = excel_file.sheet_names[3]  # Get the name of the first sheet
            df = excel_file.parse(sheet_name)
        else:
            return None, None, "Invalid file type. Please upload a CSV or Excel file."
    except Exception as e:
        print(e)
        return None, None, f"There was an error processing this file: {e}"

    # Fill NaN values with empty strings
    df = df.fillna("")

    # Extract headers and rows from DataFrame
    headers = df.columns.tolist()
    rows = df.values.tolist()

    # Process headers using the same logic as in Google Sheet processor
    processed_headers = process_headers(headers)
    # Build JSON data using the same logic as in Google Sheet processor
    records = build_json_data(processed_headers, rows)

    return records, sheet_name, None




def read_workbook_xlsx(path: str):
    def to_ascii_str(x: object) -> str:
        if x is None:
            return ""
        s = str(x)
        s = unicodedata.normalize("NFKD", s)
        s = s.encode("ascii", "ignore").decode("ascii", errors="ignore")
        s = re.sub(r"[^\x20-\x7E\s]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.dropna(how="all").dropna(axis=1, how="all")

        df = df.fillna("")
        df = df.applymap(to_ascii_str)

        df.columns = [to_ascii_str(c) for c in df.columns]
        return df

    xls = pd.ExcelFile(path, engine="openpyxl")

    raw = {name: xls.parse(sheet_name=name, dtype=str) for name in xls.sheet_names}

    return {name: _clean_df(df) for name, df in raw.items()}
