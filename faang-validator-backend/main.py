from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import sys
from typing import List, Dict, Any, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.organism_validation import PydanticValidator, generate_validation_report, process_validation_errors
from app.file_processor import parse_contents_api

app = FastAPI(title="FAANG Validator API", description="API for validating FAANG data")

# Add CORS middleware to allow cross-origin requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {"message": "FAANG Validator API is running"}

@app.post("/validate")
async def validate_file(file: UploadFile = File(...)):
    """
    Validate an uploaded file against FAANG standards.

    Args:
        file: The file to validate

    Returns:
        dict: Validation results
    """
    try:
        # Read file contents
        contents = await file.read()

        # Parse file contents - now returns all sheets
        all_sheets_data, sheet_names, error_message = parse_contents_api(contents, file.filename)

        if error_message:
            raise HTTPException(status_code=400, detail=error_message)

        # For validation, we'll use the first sheet's data
        # This maintains compatibility with the existing validation logic
        first_sheet_name = sheet_names[0]
        records = all_sheets_data[first_sheet_name]

        # Validate records from the first sheet
        validator = PydanticValidator()
        validation_results = validator.validate_with_pydantic(records)
        report = generate_validation_report(validation_results)

        valid_organisms = validation_results.get('valid_organisms', [])
        invalid_organisms = validation_results.get('invalid_organisms', [])

        # Process validation errors if there are any invalid organisms
        error_data = []
        if invalid_organisms:
            error_data = process_validation_errors(invalid_organisms, first_sheet_name)

        # Return validation results along with all sheets data
        return {
            "valid_count": len(valid_organisms),
            "invalid_count": len(invalid_organisms),
            "errors": error_data,
            "records": records,
            "all_sheets_data": all_sheets_data,
            "sheet_names": sheet_names
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
