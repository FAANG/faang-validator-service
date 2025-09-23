# Validation Service

This application provides validation services for FAANG organism metadata.

## Local Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python dash_app.py`
4. Access the application at http://localhost:8050

## Usage

The application provides two ways to validate metadata:

1. **File Upload**: Upload a CSV or Excel file containing organism metadata
2. **Google Sheet**: Provide a Google Sheet URL and worksheet number to validate

For Google Sheet validation, the application can access public Google Sheets without requiring authentication.

## Environment Variables

- `PORT`: The port on which the application will listen (default: 8050)
- `ENVIRONMENT`: Set to 'production' in production environments to disable debug mode

## Development

To modify the validation rules, check the `rulesets_pydantics` directory.
