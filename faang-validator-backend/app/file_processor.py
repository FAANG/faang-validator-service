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
        tuple: (all_sheets_data, sheet_names, error_message)
            - all_sheets_data: Dictionary with sheet names as keys and lists of dictionaries containing the parsed data as values
            - sheet_names: List of sheet names
            - error_message: Error message if any, None otherwise
    """
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if 'csv' in filename:
            # For CSV files, we only have one sheet
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            df = df.fillna("")

            # Extract headers and rows from DataFrame
            headers = df.columns.tolist()
            rows = df.values.tolist()

            # Process headers using the same logic as in Google Sheet processor
            processed_headers = process_headers(headers)
            # Build JSON data using the same logic as in Google Sheet processor
            records = build_json_data(processed_headers, rows)

            # For CSV, we use a default sheet name
            sheet_name = "Sheet 1"
            all_sheets_data = {sheet_name: records}
            sheet_names = [sheet_name]

        elif 'xls' in filename or 'xlsx' in filename:
            # For Excel files, process all sheets
            excel_file = pd.ExcelFile(io.BytesIO(decoded), engine="openpyxl")
            sheet_names = excel_file.sheet_names

            all_sheets_data = {}

            for sheet_name in sheet_names:
                df = excel_file.parse(sheet_name)
                df = df.fillna("")

                # Skip empty sheets
                if df.empty:
                    continue

                # Extract headers and rows from DataFrame
                headers = df.columns.tolist()
                rows = df.values.tolist()

                # Process headers using the same logic as in Google Sheet processor
                processed_headers = process_headers(headers)
                # Build JSON data using the same logic as in Google Sheet processor
                records = build_json_data(processed_headers, rows)

                all_sheets_data[sheet_name] = records

            # If no valid sheets were found, return an error
            if not all_sheets_data:
                return None, None, "No valid data found in the Excel file."

        else:
            return None, None, "Invalid file type. Please upload a CSV or Excel file."

    except Exception as e:
        print(e)
        return None, None, f"There was an error processing this file: {e}"

    return all_sheets_data, sheet_names, None




def parse_contents_api(contents, filename):
    """
    Parse the contents of an uploaded file from FastAPI and convert it to a structured format.

    Args:
        contents (bytes): The binary contents of the file
        filename (str): The name of the uploaded file

    Returns:
        tuple: (all_sheets_data, sheet_names, error_message)
            - all_sheets_data: Dictionary with sheet names as keys and lists of dictionaries containing the parsed data as values
            - sheet_names: List of sheet names
            - error_message: Error message if any, None otherwise
    """
    try:
        if 'csv' in filename:
            # For CSV files, we only have one sheet
            df = pd.read_csv(io.BytesIO(contents))
            df = df.fillna("")

            # Extract headers and rows from DataFrame
            headers = df.columns.tolist()
            rows = df.values.tolist()

            # Process headers using the same logic as in Google Sheet processor
            processed_headers = process_headers(headers)
            # Build JSON data using the same logic as in Google Sheet processor
            records = build_json_data(processed_headers, rows)

            # For CSV, we use a default sheet name
            sheet_name = "Sheet 1"
            all_sheets_data = {sheet_name: records}
            sheet_names = [sheet_name]

        elif 'xls' in filename or 'xlsx' in filename:
            # For Excel files, process all sheets
            excel_file = pd.ExcelFile(io.BytesIO(contents), engine="openpyxl")
            sheet_names = excel_file.sheet_names

            all_sheets_data = {}

            for sheet_name in sheet_names:
                df = excel_file.parse(sheet_name)
                df = df.fillna("")

                # Skip empty sheets
                if df.empty:
                    continue

                # Extract headers and rows from DataFrame
                headers = df.columns.tolist()
                rows = df.values.tolist()

                # Process headers using the same logic as in Google Sheet processor
                processed_headers = process_headers(headers)
                # Build JSON data using the same logic as in Google Sheet processor
                records = build_json_data(processed_headers, rows)

                all_sheets_data[sheet_name] = records

            # If no valid sheets were found, return an error
            if not all_sheets_data:
                return None, None, "No valid data found in the Excel file."

        else:
            return None, None, "Invalid file type. Please upload a CSV or Excel file."

    except Exception as e:
        print(e)
        return None, None, f"There was an error processing this file: {e}"

    return all_sheets_data, sheet_names, None


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
