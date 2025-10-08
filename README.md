# Validation Service

This application provides validation services for FAANG organism metadata.

## Local Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python dash_app.py`
4. Access the application at http://localhost:8050

## Usage

The application provides a way to validate metadata:

1. **File Upload**: Click the "Choose File" button to select a CSV or Excel file containing organism metadata
2. **Validation**: After selecting a file, click the "Validate" button to validate the metadata

## Environment Variables

- `PORT`: The port on which the application will listen (default: 8050)
- `ENVIRONMENT`: Set to 'production' in production environments to disable debug mode

## Development

To modify the validation rules, check the `rulesets_pydantics` directory.

## Code Structure

The application is organized as follows:

- `dash_app.py`: Main application file containing the Dash app and UI components
- `src/file_processor.py`: Module for file reading and processing functionality
- `src/organism_validation.py`: Module for validating organism metadata
- `src/google_sheet_processor.py`: Module for processing Google Sheets data
- `rulesets_pydantics/`: Directory containing Pydantic models for validation rules

## Dependencies

- Setuptools is pinned to a version less than 81 to avoid issues with the deprecated pkg_resources package, which is scheduled for removal in November 2025.

# Tests

python3 -m pip install -r requirements.txt

uvicorn websocket_app:app --host 127.0.0.1 --port 8000

python3 stress_test_upload.py --users 10 --concurrency 5 --payload-size 50000 --timeout 20

python3 stress_test_upload.py --users 200 --concurrency 50 --payload-size 200000 --timeout 60
