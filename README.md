# FAANG Validator Service

This application provides validation services for FAANG (Functional Annotation of Animal Genomes) organism metadata. It consists of two main components:

1. A FastAPI backend for data validation
2. A Dash frontend for user interaction

## Project Structure

- `faang-validator-backend/`: Contains the FastAPI backend code
- `faang-validator-frontend/`: Contains the Dash frontend code

## Local Setup

### Backend

1. Navigate to the backend directory:
   ```
   cd faang-validator-backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

   Dependencies include:
   - FastAPI and Uvicorn for the API server
   - Pandas for data processing
   - Google Sheets integration (gspread, google-auth)
   - Pydantic for data validation
   - Openpyxl for Excel file handling

4. Run the backend server:
   ```
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

   Alternatively, you can run:
   ```
   python main.py
   ```

The backend API will be available at http://localhost:8000. You can access the API documentation at http://localhost:8000/docs.

### Frontend

1. Navigate to the frontend directory:
   ```
   cd faang-validator-frontend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

   Dependencies include:
   - Dash and its components for the web interface
   - Requests for API communication
   - Pandas for data handling
   - Gunicorn for production deployment

4. Run the frontend server:
   ```
   python dash_app.py
   ```

   For production deployment, you can use Gunicorn:
   ```
   gunicorn dash_app:server -b 0.0.0.0:8050
   ```

The frontend will be available at http://localhost:8050.
