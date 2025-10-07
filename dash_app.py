import os
import sys
import json

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import no_update

import uuid as _uuid
import requests
from dash_extensions import WebSocket


API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
WS_BASE = os.getenv("WS_BASE_URL", API_BASE.replace("http", "ws", 1))

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.Div([
        html.H1("FAANG Validation"),

        dcc.Store(id='stored-file-data'),
        dcc.Store(id='stored-filename'),
        dcc.Store(id='error-popup-data', data={'visible': False, 'column': '', 'error': ''}),
        dcc.Store(id='client-id'),
        dcc.Store(id='stored-error-data'),

        WebSocket(id='ws', url=''),

        html.Div(
            id='error-popup-container',
            style={'display': 'none'},
            children=[
                html.Div(className='error-popup-overlay', id='error-popup-overlay'),
                html.Div(
                    className='error-popup',
                    children=[
                        html.Div(className='error-popup-close', id='error-popup-close', children='×'),
                        html.H3(className='error-popup-title', id='error-popup-title', children='Error Details'),
                        html.Div(className='error-popup-content', id='error-popup-content', children=[])
                    ]
                )
            ]
        ),

        dcc.Tabs([
            dcc.Tab(label='Samples', children=[
                html.Div([
                    html.Label("1. Upload template"),
                    html.Div([
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                html.Button(
                                    'Choose File',
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
                            style={'width': 'auto', 'margin': '10px 0'},
                            className='upload-area',
                            multiple=False
                        ),
                        html.Div(
                            html.Button(
                                'Validate',
                                id='validate-button',
                                className='validate-button',
                                disabled=True,
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
                            style={'display': 'none', 'marginLeft': '10px'}
                        ),
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    html.Div(id='selected-file-display', style={'display': 'none'}),
                ], style={'margin': '20px 0'}),

                dcc.Loading(
                    id="loading-validation",
                    type="circle",
                    children=html.Div(id='output-data-upload')
                ),

                html.Div(id='status-lines', style={'margin': '10px 0', 'color': '#333'}),
                html.Div(id='summary-buttons'),
                html.Div(id='error-table-container', style={'display': 'none'}),
                html.Div(id='excel-table-container'),
            ]),

            dcc.Tab(label='Experiments', children=[html.Div([], style={'margin': '20px 0'})]),
            dcc.Tab(label='Analysis', children=[html.Div([], style={'margin': '20px 0'})])
        ], style={'margin': '20px 0'})
    ], className='container')
])


@app.callback(
    Output('stored-file-data', 'data'),
    Output('stored-filename', 'data'),
    Output('file-chosen-text', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def store_file_data(contents, filename):
    if contents is None:
        return None, None, "No file chosen"
    return contents, filename, filename


@app.callback(
    Output('validate-button', 'disabled'),
    Output('validate-button-container', 'style'),
    Input('stored-file-data', 'data')
)
def show_and_enable_validate_button(file_data):
    if file_data is None:
        return True, {'display': 'none', 'marginLeft': '10px'}
    else:
        return False, {'display': 'block', 'marginLeft': '10px'}


@app.callback(
    Output('client-id', 'data'),
    Output('ws', 'url'),
    Input('validate-button', 'n_clicks'),
    State('client-id', 'data'),
    prevent_initial_call=True
)
def ensure_client_id(n, cid):
    if not n:
        raise PreventUpdate
    if not cid:
        cid = _uuid.uuid4().hex
    return cid, f"{WS_BASE}/ws?client_id={cid}"


@app.callback(
    Output('output-data-upload', 'children'),
    Input('validate-button', 'n_clicks'),
    State('stored-file-data', 'data'),
    State('stored-filename', 'data'),
    State('client-id', 'data'),
    prevent_initial_call=True
)
def validate_data_via_ws(n_clicks, contents, filename, client_id):
    if not n_clicks or contents is None:
        raise PreventUpdate

    try:
        requests.post(
            url=f"{API_BASE}/upload",
            data={
                "contents": contents,
                "filename": filename or "input.xlsx",
                "client_id": client_id or ""
            },
            timeout=(5, 300)
        )
    except Exception as e:
        return html.Div([
            html.H5(filename or "file"),
            html.P(f"Failed to start validation: {e}", style={'color': 'red'})
        ])

    return html.Div([html.Div("Started… waiting for server updates.")])


@app.callback(
    Output('status-lines', 'children'),
    Output('summary-buttons', 'children'),
    Output('stored-error-data', 'data'),
    Output('excel-table-container', 'children'),
    Input('ws', 'message'),
    State('status-lines', 'children'),
    prevent_initial_call=True
)
def on_ws_message(message, existing_status):
    if not message:
        raise PreventUpdate
    try:
        payload = json.loads(message['data'])
    except Exception:
        raise PreventUpdate

    typ = payload.get("type")
    status_children = existing_status or []

    if typ == "status":
        return status_children + [html.Div(payload.get("msg", ""))], no_update, no_update, no_update

    if typ == "error":
        return (status_children + [html.Div(f"ERROR: {payload.get('detail','')}", style={'color': 'red'})],
                no_update, no_update, no_update)

    if typ == "result":
        valid = payload.get("valid_count", 0)
        invalid = payload.get("invalid_count", 0)
        err = payload.get("error_table", [])
        cols = payload.get("columns", [])
        preview = payload.get("data_preview", [])

        summary = html.Div([
            html.Button(
                f"Valid organisms: {valid}", id='passed-validation-button', className='summary-button success'
            ),
            html.Button(
                f"Invalid organisms: {invalid}", id='issues-validation-button',
                className='summary-button warning', n_clicks=0
            ),
        ], style={'display': 'flex', 'justifyContent': 'center', 'gap': '20px', 'margin': '20px 0'})

        excel_children = html.Div([
            html.H3("3. Excel File Data (preview)"),
            dash_table.DataTable(
                id='excel-data-table',
                data=preview,
                columns=[{'name': c, 'id': c} for c in cols],
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248,248,248)'}]
            )
        ], style={'margin': '20px 0'})

        return status_children, summary, err, excel_children

    if typ == "done":
        ok = payload.get("ok", False)
        return (status_children + [html.Div("Completed." if ok else "Failed.", style={'fontWeight': 'bold'})],
                no_update, no_update, no_update)

    raise PreventUpdate


@app.callback(
    Output('error-table-container', 'children'),
    Output('error-table-container', 'style'),
    Input('issues-validation-button', 'n_clicks'),
    State('error-table-container', 'style'),
    State('stored-error-data', 'data'),
    prevent_initial_call=True
)
def toggle_error_table(n_clicks, current_style, error_data):
    if not n_clicks or not error_data:
        return [], {'display': 'none'}

    is_visible = current_style and current_style.get('display') == 'block'
    if is_visible:
        return [], {'display': 'none'}
    else:
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
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
                    {'if': {'column_id': 'Column Name'},
                     'color': '#ff0000', 'fontWeight': 'bold', 'cursor': 'pointer', 'textDecoration': 'underline'}
                ],
                tooltip_data=[
                    {'Column Name': {'value': 'Click to see error details', 'type': 'markdown'}}
                    for _ in error_data
                ],
                tooltip_duration=None,
                cell_selectable=True
            )
        ]
        return error_table, {'display': 'block'}


@app.callback(
    Output('error-popup-container', 'style'),
    Output('error-popup-title', 'children'),
    Output('error-popup-content', 'children'),
    Input('error-table', 'active_cell'),
    State('error-table', 'data'),
    prevent_initial_call=True
)
def show_error_popup(active_cell, data):
    if active_cell is None or active_cell.get('column_id') != 'Column Name':
        return {'display': 'none'}, 'Error Details', []

    row_idx = active_cell['row']
    column_name = data[row_idx]['Column Name']
    error_message = data[row_idx]['Error']

    error_parts = error_message.split('; ')
    error_elements = [html.P(error, style={'color': '#ff0000'}) for error in error_parts]

    return {'display': 'block'}, f"Error in column: {column_name}", [
        html.P(f"Sample: {data[row_idx]['Sample Name']}"),
        html.P(f"Sheet: {data[row_idx]['Sheet']}"),
        html.P("Error details:"),
        html.Div(error_elements, style={'marginLeft': '20px'})
    ]


@app.callback(
    Output('error-popup-container', 'style', allow_duplicate=True),
    Input('error-popup-close', 'n_clicks'),
    Input('error-popup-overlay', 'n_clicks'),
    prevent_initial_call=True
)
def close_error_popup(close_clicks, overlay_clicks):
    return {'display': 'none'}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('ENVIRONMENT', 'development') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
