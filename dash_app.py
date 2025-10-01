import json
import sys
import os

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, MATCH, ALL
import pandas as pd
from dash.exceptions import PreventUpdate
import uuid

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.organism_validation import PydanticValidator, generate_validation_report, process_validation_errors
from src.file_processor import parse_contents, read_workbook_xlsx

# Initialize the Dash app
# Set suppress_callback_exceptions=True to allow callbacks for components that are created dynamically
# (like the issues-validation-button which is created after validation)
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # Expose server variable for gunicorn

# --- App Layout ---
app.layout = html.Div([
    html.Div([
        html.H1("FAANG Validation"),

        # Store for uploaded file data
        dcc.Store(id='stored-file-data'),
        dcc.Store(id='stored-filename'),
        dcc.Store(id='error-popup-data', data={'visible': False, 'column': '', 'error': ''}),

        # Error popup
        html.Div(
            id='error-popup-container',
            style={'display': 'none'},
            children=[
                html.Div(
                    className='error-popup-overlay',
                    id='error-popup-overlay'
                ),
                html.Div(
                    className='error-popup',
                    children=[
                        html.Div(
                            className='error-popup-close',
                            id='error-popup-close',
                            children='×'
                        ),
                        html.H3(
                            className='error-popup-title',
                            id='error-popup-title',
                            children='Error Details'
                        ),
                        html.Div(
                            className='error-popup-content',
                            id='error-popup-content',
                            children=[]
                        )
                    ]
                )
            ]
        ),

        # Tabs
        dcc.Tabs([
            # Samples Tab
            dcc.Tab(label='Samples', children=[
                # File Upload
                html.Div([
                    html.Label("1. Upload template"),
                    html.Div([
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                html.Button('Choose File', 
                                    className='upload-button',
                                    style={
                                        'backgroundColor': '#cccccc',
                                        'color': 'black',
                                        'padding': '10px 20px',
                                        'border': 'none',
                                        'borderRadius': '4px',
                                        'cursor': 'pointer',
                                    }
                                ),
                                html.Div('No file chosen', id='file-chosen-text')
                            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'}),
                            style={
                                'width': 'auto',
                                'margin': '10px 0',
                            },
                            className='upload-area',
                            multiple=False
                        ),
                        # Validate button container - initially hidden
                        html.Div(
                            html.Button(
                                'Validate',
                                id='validate-button',
                                className='validate-button',
                                disabled=True,  # Initially disabled until a file is uploaded
                                style={
                                    'backgroundColor': '#4CAF50',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'border': 'none',
                                    'borderRadius': '4px',
                                    'cursor': 'pointer',
                                    'fontSize': '16px',
                                }
                            ),
                            id='validate-button-container',
                            style={'display': 'none', 'marginLeft': '10px'}  # Initially hidden
                        ),
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    html.Div(id='selected-file-display', style={'display': 'none'}),
                ], style={'margin': '20px 0'}),

                dcc.Loading(
                    id="loading-validation",
                    type="circle",
                    children=html.Div(id='output-data-upload')
                )
            ]),

            # Experiments Tab (empty for now)
            dcc.Tab(label='Experiments', children=[
                html.Div([], style={'margin': '20px 0'})
            ]),

            # Analysis Tab (empty for now)
            dcc.Tab(label='Analysis', children=[
                html.Div([], style={'margin': '20px 0'})
            ])
        ], style={'margin': '20px 0'})
    ], className='container')
])


# Callback to store uploaded file data and display filename
@app.callback(
    [Output('stored-file-data', 'data'),
     Output('stored-filename', 'data'),
     Output('file-chosen-text', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def store_file_data(contents, filename):
    if contents is None:
        return None, None, "No file chosen"

    # Store the file data and filename
    return contents, filename, filename

# Callback to show and enable validate button when a file is uploaded
@app.callback(
    [Output('validate-button', 'disabled'),
     Output('validate-button-container', 'style')],
    [Input('stored-file-data', 'data')]
)
def show_and_enable_validate_button(file_data):
    if file_data is None:
        # No file selected: button is disabled and hidden
        return True, {'display': 'none', 'marginLeft': '10px'}
    else:
        # File selected: button is enabled and visible
        return False, {'display': 'block', 'marginLeft': '10px'}

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
    print(json_data)
    # Use the records directly for validation
    validation_results = validator.validate_with_pydantic(records)
    report = generate_validation_report(validation_results)

    valid_organisms = validation_results.get('valid_organisms', [])
    invalid_organisms = validation_results.get('invalid_organisms', [])

    # Process validation errors if there are any invalid organisms
    error_data = []
    if invalid_organisms:
        error_data = process_validation_errors(invalid_organisms, sheet_name)

    # Create a summary display
    summary_components = [
        # Store for error data
        dcc.Store(id='stored-error-data', data=error_data),

        html.Div([
            html.Button(
                f"Valid organisms: {len(valid_organisms)}",
                id='passed-validation-button',
                className='summary-button success',
            ),
            html.Button(
                f"Invalid organisms: {len(invalid_organisms)}",
                id='issues-validation-button',
                className='summary-button warning',
                n_clicks=0  # Initialize click counter
            ),
        ], style={'display': 'flex', 'justifyContent': 'center', 'gap': '20px', 'margin': '20px 0'}),

        # Container for error table that will be populated by callback
        html.Div(id='error-table-container', style={'display': 'none'}),

        # Display the Excel file as a table
        html.Div([
            html.H3("3. Excel File Data"),
            dash_table.DataTable(
                id='excel-data-table',
                data=[{k: json.dumps(v) if not isinstance(v, (str, int, float, bool)) else v for k, v in record.items()} for record in records],
                columns=[{'name': k, 'id': k} for k in records[0].keys()] if records else [],
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
        ], style={'margin': '20px 0'})
    ]

    # We'll show the error table through a callback instead

    return html.Div(summary_components)

# Callback to show/hide error table when "Invalid organisms" button is clicked
@app.callback(
    Output('error-table-container', 'children'),
    Output('error-table-container', 'style'),
    [Input('issues-validation-button', 'n_clicks')],
    [State('error-table-container', 'style'),
     State('stored-error-data', 'data')]
)
def toggle_error_table(n_clicks, current_style, error_data):
    # If button hasn't been clicked or there's no error data, don't show table
    if n_clicks is None or n_clicks == 0 or not error_data:
        return [], {'display': 'none'}

    # Toggle visibility based on current state
    is_visible = current_style and current_style.get('display') == 'block'

    if is_visible:
        # If currently visible, hide it
        return [], {'display': 'none'}
    else:
        # If currently hidden, show it
        # Create the error table
        error_table = [
            html.H3("2. Conversion and Validation results"),
            dash_table.DataTable(
                id='error-table',
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
                    },
                    {
                        'if': {'column_id': 'Column Name'},
                        'color': '#ff0000',
                        'fontWeight': 'bold',
                        'cursor': 'pointer',
                        'textDecoration': 'underline'
                    }
                ],
                tooltip_data=[
                    {
                        'Column Name': {'value': 'Click to see error details', 'type': 'markdown'}
                    } for row in error_data
                ],
                tooltip_duration=None,
                cell_selectable=True
            )
        ]

        # Return the table and set display style to block
        return error_table, {'display': 'block'}

# Callback to show error popup when a cell in the "Column Name" column is clicked
@app.callback(
    [Output('error-popup-container', 'style'),
     Output('error-popup-title', 'children'),
     Output('error-popup-content', 'children')],
    [Input('error-table', 'active_cell')],
    [State('error-table', 'data')]
)
def show_error_popup(active_cell, data):
    if active_cell is None or active_cell['column_id'] != 'Column Name':
        return {'display': 'none'}, 'Error Details', []

    row_idx = active_cell['row']
    column_name = data[row_idx]['Column Name']
    error_message = data[row_idx]['Error']

    # Split error message by semicolons and create a list of paragraph elements
    error_parts = error_message.split('; ')
    error_elements = [html.P(error, style={'color': '#ff0000'}) for error in error_parts]

    return {'display': 'block'}, f"Error in column: {column_name}", [
        html.P(f"Sample: {data[row_idx]['Sample Name']}"),
        html.P(f"Sheet: {data[row_idx]['Sheet']}"),
        html.P("Error details:"),
        html.Div(
            error_elements,
            style={'marginLeft': '20px'}
        )
    ]

# Callback to close error popup when close button or overlay is clicked
@app.callback(
    Output('error-popup-container', 'style', allow_duplicate=True),
    [Input('error-popup-close', 'n_clicks'),
     Input('error-popup-overlay', 'n_clicks')],
    prevent_initial_call=True
)
def close_error_popup(close_clicks, overlay_clicks):
    return {'display': 'none'}

# --- Run the app ---
if __name__ == '__main__':
    # Get port from environment variable or use 8050 as default
    port = int(os.environ.get('PORT', 8050))

    # Determine if we're in a production environment
    debug = os.environ.get('ENVIRONMENT', 'development') != 'production'

    app.run(host='0.0.0.0', port=port, debug=debug)
