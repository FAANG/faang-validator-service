import base64
import io
import json
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import sys
import os
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.organism_validation import PydanticValidator, generate_validation_report
from src.google_sheet_processor import GoogleSheetProcessor, process_headers, build_json_data

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server  # Expose server variable for gunicorn

# --- App Layout ---
app.layout = html.Div([
    html.H1("FAANG Metadata Validator"),

    # Tabs
    dcc.Tabs([
        # Tab 1: File Upload
        dcc.Tab(label='File Upload', children=[
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select Files')
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px',
                    'transition': 'all 0.3s ease'
                },
                className='upload-area',
                multiple=False
            ),
            dcc.Loading(
                id="loading-upload",
                type="circle",
                children=html.Div(id='output-data-upload')
            ),
        ]),

        # Tab 2: Google Sheet URL
        dcc.Tab(label='Google Sheet URL', children=[
            html.Div([
                html.H3("Validate Google Sheet"),
                html.P("Enter a Google Sheet URL to validate organism data (sheet 0) and origin ID data (sheet 1):"),

                # Google Sheet URL input
                html.Div([
                    html.Label("Google Sheet URL:"),
                    dcc.Input(
                        id='google-sheet-url',
                        type='text',
                        placeholder='Enter Google Sheet URL',
                        style={'width': '100%', 'marginBottom': '20px'}
                    ),
                ]),


                # Submit button
                html.Button(
                    'Validate', 
                    id='validate-button', 
                    n_clicks=0,
                    style={
                        'backgroundColor': '#4CAF50',
                        'color': 'white',
                        'padding': '10px 20px',
                        'border': 'none',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'marginBottom': '20px',
                        'transition': 'background-color 0.3s'
                    },
                    # Using the Dash clientside_callback feature for hover effects
                    className='validate-button'
                ),

                # Output area with loading spinner
                dcc.Loading(
                    id="loading-validation",
                    type="circle",
                    children=html.Div(id='google-sheet-output')
                )
            ], style={'padding': '20px'})
        ])
    ])
])

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume you have a header row
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename or 'xlsx' in filename:
            # Assume you have a header row
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None, "Invalid file type. Please upload a CSV or Excel file."
    except Exception as e:
        print(e)
        return None, f"There was an error processing this file: {e}"

    # Extract headers and rows from DataFrame
    headers = df.columns.tolist()

    rows = df.values.tolist()

    # Process headers using the same logic as in Google Sheet processor
    processed_headers = process_headers(headers)
    # Build JSON data using the same logic as in Google Sheet processor
    records = build_json_data(processed_headers, rows)

    # Convert to JSON format
    json_data = json.dumps(records)

    return records, None

@app.callback(
    Output('output-data-upload', 'children'),
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_output(contents, filename):
    if contents is None:
        return []

    records, error_message = parse_contents(contents, filename)
    if error_message:
        return html.Div([
            html.H5(filename),
            html.P(error_message, style={'color': 'red'})
        ])

    validator = PydanticValidator()


    # Convert records to JSON format
    json_data = json.dumps(records)

    # Use the records directly for validation
    validation_results = validator.validate_with_pydantic(records)
    report = generate_validation_report(validation_results)

    valid_organisms = validation_results.get('valid_organisms', [])
    invalid_organisms = validation_results.get('invalid_organisms', [])

    # Create a summary display
    summary_components = [
        html.H5(filename),
        html.H3("Validation Summary"),
        dcc.Textarea(
            value=report,
            style={'width': '100%', 'height': 300},
            readOnly=True
        )
    ]

    # Only show invalid organisms table if there are any
    if invalid_organisms:
        # Preprocess data to handle complex fields like 'Health Status'
        processed_data = []
        for org in invalid_organisms:
            org_data = org['data'].copy()
            # Convert 'Health Status' to string if it's a complex structure
            # if 'Health Status' in org_data and isinstance(org_data['Health Status'], list):
            #     health_statuses = [status.get('text', '') for status in org_data['Health Status']]
            #     org_data['Health Status'] = ', '.join(health_statuses)

            # Convert 'Child Of' to string if it's a list
            if 'Child Of' in org_data and isinstance(org_data['Child Of'], list):
                org_data['Child Of'] = ', '.join(filter(None, org_data['Child Of']))
            processed_data.append(org_data)

        # Create a table for field-specific errors
        error_data = []
        for org in invalid_organisms:
            sample_name = org['sample_name']
            field_errors = org['errors'].get('field_errors', {})

            for field, errors in field_errors.items():
                error_data.append({
                    'Sample Name': sample_name,
                    'Field': field,
                    'Error': '; '.join(errors)
                })

        summary_components.extend([
            html.H3("Validation Errors by Field"),
            dash_table.DataTable(
                data=error_data,
                columns=[
                    {'name': 'Sample Name', 'id': 'Sample Name'},
                    {'name': 'Field', 'id': 'Field'},
                    {'name': 'Error', 'id': 'Error'}
                ],
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ]
            )
        ])

    return html.Div(summary_components)

# Function to extract spreadsheet ID from Google Sheet URL
def extract_spreadsheet_id(url):
    # Pattern to match Google Sheets URL
    pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

# Callback for Google Sheet validation
@app.callback(
    Output('google-sheet-output', 'children'),
    [Input('validate-button', 'n_clicks')],
    [State('google-sheet-url', 'value')]
)
def validate_google_sheet(n_clicks, url):
    if n_clicks == 0 or not url:
        return []

    # Extract spreadsheet ID from URL
    spreadsheet_id = extract_spreadsheet_id(url)
    if not spreadsheet_id:
        return html.Div([
            html.P("Invalid Google Sheet URL. Please provide a valid URL.", style={'color': 'red'})
        ])

    try:
        # Initialize GoogleSheetProcessor
        processor = GoogleSheetProcessor(spreadsheet_id)

        # Process sheet 0 (organism data)
        organism_records = processor.process_spreadsheet(0)

        # Validate organism data
        validator = PydanticValidator()
        organism_validation_results = validator.validate_with_pydantic(organism_records)
        organism_report = generate_validation_report(organism_validation_results)

        valid_organisms = organism_validation_results.get('valid_organisms', [])
        invalid_organisms = organism_validation_results.get('invalid_organisms', [])

        # Create organism summary components
        organism_summary_components = [
            html.H3("Organism Validation Summary"),
            dcc.Textarea(
                value=organism_report,
                style={'width': '100%', 'height': 300},
                readOnly=True
            )
        ]

        # Only show invalid organisms table if there are any
        if invalid_organisms:
            # Preprocess data to handle complex fields like 'Health Status'
            processed_data = []
            for org in invalid_organisms:
                org_data = org['data'].copy()
                # Convert 'Health Status' to string if it's a complex structure
                if 'Health Status' in org_data and isinstance(org_data['Health Status'], list):
                    health_statuses = [status.get('text', '') for status in org_data['Health Status']]
                    org_data['Health Status'] = ', '.join(health_statuses)

                # Convert 'Child Of' to string if it's a list
                if 'Child Of' in org_data and isinstance(org_data['Child Of'], list):
                    org_data['Child Of'] = ', '.join(filter(None, org_data['Child Of']))
                processed_data.append(org_data)

            # Create a table for field-specific errors
            error_data = []
            for org in invalid_organisms:
                sample_name = org['sample_name']
                field_errors = org['errors'].get('field_errors', {})

                for field, errors in field_errors.items():
                    error_data.append({
                        'Sample Name': sample_name,
                        'Field': field,
                        'Error': '; '.join(errors)
                    })

            organism_summary_components.extend([
                html.H3("Validation Errors by Field"),
                dash_table.DataTable(
                    data=error_data,
                    columns=[
                        {'name': 'Sample Name', 'id': 'Sample Name'},
                        {'name': 'Field', 'id': 'Field'},
                        {'name': 'Error', 'id': 'Error'}
                    ],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ]
                )
            ])

        # Process sheet 1 (origin ID data)
        try:
            origin_id_records = processor.process_spreadsheet(1)

            # Create origin ID summary components
            origin_id_summary_components = [
                html.H3("Origin ID Data"),
                dash_table.DataTable(
                    data=origin_id_records,
                    columns=[{'name': i, 'id': i} for i in origin_id_records[0].keys()] if origin_id_records else [],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ]
                )
            ]
        except Exception as e:
            origin_id_summary_components = [
                html.H3("Origin ID Data"),
                html.P(f"Error processing Origin ID data: {str(e)}", style={'color': 'red'})
            ]

        # Create tabs for organism and origin ID validation results
        return html.Div([
            dcc.Tabs([
                dcc.Tab(label='Organism Validation', children=[
                    html.Div(organism_summary_components, style={'padding': '20px'})
                ]),
                dcc.Tab(label='Origin ID Data', children=[
                    html.Div(origin_id_summary_components, style={'padding': '20px'})
                ])
            ])
        ])
    except Exception as e:
        return html.Div([
            html.P(f"Error processing Google Sheet: {str(e)}", style={'color': 'red'})
        ])

# --- Run the app ---
if __name__ == '__main__':
    # Get port from environment variable or use 8050 as default
    port = int(os.environ.get('PORT', 8050))

    # Determine if we're in a production environment
    debug = os.environ.get('ENVIRONMENT', 'development') != 'production'

    app.run(host='0.0.0.0', port=port, debug=debug)
