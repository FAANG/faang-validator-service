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

## Usage

The application provides a way to validate metadata:

1. **File Upload**: Click the "Choose File" button to select a CSV or Excel file containing organism metadata
2. **Validation**: After selecting a file, click the "Validate" button to validate the metadata

## Environment Variables

### Frontend Environment Variables
- `BACKEND_API_URL`: URL of the backend API (default: http://localhost:8000)
- `PORT`: Port for the frontend server (default: 8050)
- `ENVIRONMENT`: Set to 'production' for production mode (default: 'development')

### Setting Environment Variables

#### On Linux/macOS:
```bash
# For frontend
export BACKEND_API_URL=http://api.example.com
export PORT=8080
export ENVIRONMENT=production

# Then run the application
python dash_app.py
```

#### On Windows:
```cmd
# For frontend
set BACKEND_API_URL=http://api.example.com
set PORT=8080
set ENVIRONMENT=production

# Then run the application
python dash_app.py
```

#### Using a .env file (recommended for development):
Create a `.env` file in the frontend directory with the following content:
```
BACKEND_API_URL=http://api.example.com
PORT=8080
ENVIRONMENT=production
```

Note: To use a .env file, you'll need to install the python-dotenv package and modify the application to load environment variables from the .env file.

## Docker Deployment

### Frontend Docker Deployment

The frontend includes a Dockerfile that can be used to build and run the application in a Docker container.

1. Build the Docker image:
   ```bash
   cd faang-validator-frontend
   docker build -t faang-validator-frontend .
   ```

2. Run the Docker container:
   ```bash
   docker run -p 8050:8080 -e BACKEND_API_URL=http://backend-host:8000 faang-validator-frontend
   ```

   Replace `http://backend-host:8000` with the actual URL of your backend API.

### Backend Docker Deployment

The backend doesn't include a Dockerfile, but you can create one with the following content:

```dockerfile
# Use Python 3.10 as the base image
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Command to run the application
CMD uvicorn main:app --host 0.0.0.0 --port 8000
```

1. Create a file named `Dockerfile` in the `faang-validator-backend` directory with the content above.

2. Build the Docker image:
   ```bash
   cd faang-validator-backend
   docker build -t faang-validator-backend .
   ```

3. Run the Docker container:
   ```bash
   docker run -p 8000:8000 faang-validator-backend
   ```

### Docker Compose (Optional)

For a complete deployment with both frontend and backend, you can use Docker Compose. Create a `docker-compose.yml` file in the root directory with the following content:

```yaml
version: '3'

services:
  backend:
    build: ./faang-validator-backend
    ports:
      - "8000:8000"

  frontend:
    build: ./faang-validator-frontend
    ports:
      - "8050:8080"
    environment:
      - BACKEND_API_URL=http://backend:8000
    depends_on:
      - backend
```

Run both services with:
```bash
docker-compose up
```

## Development

To modify the validation rules, check the `rulesets_pydantics` directory.

## Code Structure

The application is organized as follows:

### Frontend
- `faang-validator-frontend/dash_app.py`: Main frontend application file containing the Dash app and UI components
- `faang-validator-frontend/assets/`: Directory containing CSS and other frontend assets

### Backend
- `faang-validator-backend/main.py`: Main backend application file containing the FastAPI app
- `faang-validator-backend/src/file_processor.py`: Module for file reading and processing functionality
- `faang-validator-backend/src/organism_validation.py`: Module for validating organism metadata
- `faang-validator-backend/src/google_sheet_processor.py`: Module for processing Google Sheets data
- `rulesets_pydantics/`: Directory containing Pydantic models for validation rules

## Dependencies

- Setuptools is pinned to a version less than 81 to avoid issues with the deprecated pkg_resources package, which is scheduled for removal in November 2025.

## Troubleshooting

### Common Issues

#### Backend Issues

1. **Error: Address already in use**
   - Problem: The port 8000 is already in use by another application.
   - Solution: Change the port number or stop the other application using the port.
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

2. **ModuleNotFoundError**
   - Problem: Python can't find a required module.
   - Solution: Make sure you've activated the virtual environment and installed all dependencies.
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Google Sheets API Authentication Error**
   - Problem: Issues with Google Sheets API authentication.
   - Solution: Ensure you have the correct credentials and they are properly configured.

#### Frontend Issues

1. **Cannot connect to backend API**
   - Problem: The frontend can't connect to the backend API.
   - Solution: Check that the backend is running and the BACKEND_API_URL environment variable is set correctly.
   ```bash
   export BACKEND_API_URL=http://localhost:8000
   ```

2. **File upload issues**
   - Problem: Files aren't being uploaded or processed correctly.
   - Solution: Check the file format and ensure it meets the expected structure.

### Getting Help

If you encounter issues not covered here, please open an issue on the GitHub repository with:
- A clear description of the problem
- Steps to reproduce the issue
- Any error messages you're receiving
- Your environment details (OS, Python version, etc.)
