import json
import sys
import os

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, MATCH, ALL
import pandas as pd

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.organism_validation import PydanticValidator, generate_validation_report, process_validation_errors
from src.file_processor import parse_contents, read_workbook_xlsx

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server  # Expose server variable for gunicorn

# --- App Layout ---
app.layout = html.Div([
    html.Div([
        html.H1("FAANG Metadata Validator"),

        # Store for uploaded file data
        dcc.Store(id='stored-file-data'),
        dcc.Store(id='stored-filename'),

        # File Upload
        html.Div([
            html.Label("Select a file to validate:"),
            dcc.Upload(
                id='upload-data',
                children=html.Button('Choose File', className='upload-button'),
                style={
                    'width': '100%',
                    'margin': '10px 0',
                },
                className='upload-area',
                multiple=False
            ),
            html.Div(id='selected-file-display'),
            html.Button(
                'Validate',
                id='validate-button',
                className='validate-button',
                style={
                    'backgroundColor': '#4CAF50',
                    'color': 'white',
                    'padding': '10px 20px',
                    'margin': '10px 0',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'fontSize': '16px',
                    'display': 'none'  # Initially hidden until a file is uploaded
                }
            ),
        ], style={'margin': '20px 0'}),

        dcc.Loading(
            id="loading-validation",
            type="circle",
            children=html.Div(id='output-data-upload')
        )
    ], className='container')
])


# Callback to store uploaded file data and display filename
@app.callback(
    [Output('stored-file-data', 'data'),
     Output('stored-filename', 'data'),
     Output('selected-file-display', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def store_file_data(contents, filename):
    if contents is None:
        return None, None, ""

    # Store the file data and filename
    return contents, filename, html.Div([
        html.I(className="fas fa-file"),
        f" {filename}"
    ], style={'margin': '10px 0'})

# Callback to show validate button when a file is uploaded
@app.callback(
    Output('validate-button', 'style'),
    [Input('stored-file-data', 'data')]
)
def show_validate_button(file_data):
    if file_data is None:
        return {'display': 'none'}

    return {
        'backgroundColor': '#4CAF50',
        'color': 'white',
        'padding': '10px 20px',
        'margin': '10px 0',
        'border': 'none',
        'borderRadius': '4px',
        'cursor': 'pointer',
        'fontSize': '16px',
        'display': 'block'
    }

# Callback to validate data when button is clicked
@app.callback(
    Output('output-data-upload', 'children'),
    [Input('validate-button', 'n_clicks')],
    [State('stored-file-data', 'data'),
     State('stored-filename', 'data')]
)
def validate_data(n_clicks, contents, filename):
    if n_clicks is None or contents is None:
        return []

    records, sheet_name, error_message = parse_contents(contents, filename)
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
        html.H3("Validation Summary"),
        dcc.Textarea(
            value=report,
            style={'width': '100%', 'height': 120, 'align': 'center'},
            readOnly=True
        )
    ]

    # Only show invalid organisms table if there are any
    if invalid_organisms:
        # Process validation errors
        error_data = process_validation_errors(invalid_organisms, sheet_name)

        summary_components.extend([
            html.H3("Validation Errors by Sheet and Column"),
            dash_table.DataTable(
                data=error_data,
                columns=[
                    {'name': 'Sheet', 'id': 'Sheet'},
                    {'name': 'Sample Name', 'id': 'Sample Name'},
                    {'name': 'Column Name', 'id': 'Column Name'},
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

# --- Run the app ---
if __name__ == '__main__':
    # Get port from environment variable or use 8050 as default
    port = int(os.environ.get('PORT', 8050))

    # Determine if we're in a production environment
    debug = os.environ.get('ENVIRONMENT', 'development') != 'production'

    app.run(host='0.0.0.0', port=port, debug=debug)
