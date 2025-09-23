from pydantic import BaseModel, Field, validator, AnyUrl
from organism_validator_classes import OntologyValidator
from typing import List, Optional, Union, Literal, Dict, Any
import re

from .standard_ruleset import SampleCoreMetadata

class FAANGOrganoidSample(BaseModel):
    organoid: List[Dict[str, Any]] = Field(..., description="List of organoid samples")

    class Config:
        extra = "forbid"
        validate_by_name = True
        validate_default = True
        validate_assignment = True

    @field_validator('organoid')
    def validate_organoid_samples(cls, v):
        if not v or not isinstance(v, list):
            raise ValueError("organoid must be a non-empty list")

        for sample in v:
            # Validate required fields
            if "Sample Name" not in sample:
                raise ValueError("Each organoid sample must have a 'Sample Name'")
            if "Material" not in sample:
                raise ValueError("Each organoid sample must have a 'Material'")
            if "Term Source ID" not in sample:
                raise ValueError("Each organoid sample must have a 'Material Term Source ID'")
            if "Project" not in sample:
                raise ValueError("Each organoid sample must have a 'Project'")
            if "Organ Model" not in sample:
                raise ValueError("Each organoid sample must have an 'Organ Model'")
            if "Organ Model Term Source ID" not in sample:
                raise ValueError("Each organoid sample must have an 'Organ Model Term Source ID'")
            if "Freezing Method" not in sample:
                raise ValueError("Each organoid sample must have a 'Freezing Method'")
            if "Organoid Passage" not in sample:
                raise ValueError("Each organoid sample must have an 'Organoid Passage'")
            if "Organoid Passage Unit" not in sample:
                raise ValueError("Each organoid sample must have an 'Organoid Passage Unit'")
            if "Organoid Passage Protocol" not in sample:
                raise ValueError("Each organoid sample must have an 'Organoid Passage Protocol'")
            if "Type Of Organoid Culture" not in sample:
                raise ValueError("Each organoid sample must have a 'Type Of Organoid Culture'")
            if "Growth Environment" not in sample:
                raise ValueError("Each organoid sample must have a 'Growth Environment'")
            if "Derived From" not in sample:
                raise ValueError("Each organoid sample must have a 'Derived From'")

            # Validate material
            if sample["Material"] != "organoid":
                raise ValueError(f"Material must be 'organoid', got '{sample['Material']}'")

            # Validate project
            if sample["Project"] != "FAANG":
                raise ValueError(f"Project must be 'FAANG', got '{sample['Project']}'")

            # Validate secondary project is a list
            if "Secondary Project" in sample and not isinstance(sample["Secondary Project"], list):
                raise ValueError("Secondary Project must be a list")

            # Validate freezing method
            valid_freezing_methods = [
                "ambient temperature", "cut slide", "fresh", "frozen, -70 freezer",
                "frozen, -150 freezer", "frozen, liquid nitrogen", "frozen, vapor phase",
                "paraffin block", "RNAlater, frozen", "TRIzol, frozen"
            ]
            if sample["Freezing Method"] not in valid_freezing_methods:
                raise ValueError(f"Freezing Method must be one of {valid_freezing_methods}, got '{sample['Freezing Method']}'")

            # Validate conditionally required fields based on freezing method
            if sample["Freezing Method"] != "fresh":
                if "Freezing Date" not in sample or not sample["Freezing Date"]:
                    raise ValueError("Freezing Date is required when Freezing Method is not 'fresh'")
                if "Freezing Date Unit" not in sample or not sample["Freezing Date Unit"]:
                    raise ValueError("Freezing Date Unit is required when Freezing Method is not 'fresh'")
                if "Freezing Protocol" not in sample or not sample["Freezing Protocol"]:
                    raise ValueError("Freezing Protocol is required when Freezing Method is not 'fresh'")

            # Validate organoid passage unit
            if sample["Organoid Passage Unit"] != "passages":
                raise ValueError(f"Organoid Passage Unit must be 'passages', got '{sample['Organoid Passage Unit']}'")

            # Validate type of organoid culture
            valid_culture_types = ["2D", "3D"]
            if sample["Type Of Organoid Culture"] not in valid_culture_types:
                raise ValueError(f"Type Of Organoid Culture must be one of {valid_culture_types}, got '{sample['Type Of Organoid Culture']}'")

            # Validate growth environment
            valid_growth_environments = ["matrigel", "liquid suspension", "adherent"]
            if sample["Growth Environment"] not in valid_growth_environments:
                raise ValueError(f"Growth Environment must be one of {valid_growth_environments}, got '{sample['Growth Environment']}'")

            # Validate freezing date format if provided
            if "Freezing Date" in sample and sample["Freezing Date"]:
                pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])|[12]\d{3}-(0[1-9]|1[0-2])|[12]\d{3}$'
                if not re.match(pattern, sample["Freezing Date"]):
                    raise ValueError(f"Invalid freezing date format: {sample['Freezing Date']}. Must match YYYY-MM-DD, YYYY-MM, or YYYY pattern")

            # Validate freezing date unit if provided
            if "Freezing Date Unit" in sample and sample["Freezing Date Unit"]:
                valid_date_units = ["YYYY-MM-DD", "YYYY-MM", "YYYY", "restricted access"]
                if sample["Freezing Date Unit"] not in valid_date_units:
                    raise ValueError(f"Freezing Date Unit must be one of {valid_date_units}, got '{sample['Freezing Date Unit']}'")

            # Validate number of frozen cells unit if provided
            if "Number Of Frozen Cells Unit" in sample and sample["Number Of Frozen Cells Unit"]:
                if sample["Number Of Frozen Cells Unit"] != "organoids":
                    raise ValueError(f"Number Of Frozen Cells Unit must be 'organoids', got '{sample['Number Of Frozen Cells Unit']}'")

            # Validate stored oxygen level unit if provided
            if "Stored Oxygen Level Unit" in sample and sample["Stored Oxygen Level Unit"]:
                if sample["Stored Oxygen Level Unit"] != "%":
                    raise ValueError(f"Stored Oxygen Level Unit must be '%', got '{sample['Stored Oxygen Level Unit']}'")

            # Validate incubation temperature unit if provided
            if "Incubation Temperature Unit" in sample and sample["Incubation Temperature Unit"]:
                valid_temp_units = ["Celsius", "Fahrenheit", "Kelvin"]
                if sample["Incubation Temperature Unit"] not in valid_temp_units:
                    raise ValueError(f"Incubation Temperature Unit must be one of {valid_temp_units}, got '{sample['Incubation Temperature Unit']}'")

        return v
