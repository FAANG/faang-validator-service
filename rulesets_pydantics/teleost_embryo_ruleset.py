from pydantic import BaseModel, Field, validator, AnyUrl
from organism_validator_classes import OntologyValidator
from typing import List, Optional, Union, Literal, Dict, Any
import re

from .standard_ruleset import SampleCoreMetadata

class FAANGTeleostEmbryoSample(BaseModel):
    teleost_embryo: List[Dict[str, Any]] = Field(..., description="List of teleost embryo specimens")

    class Config:
        extra = "forbid"
        validate_by_name = True
        validate_default = True
        validate_assignment = True

    @field_validator('teleost_embryo')
    def validate_teleost_embryo_samples(cls, v):
        if not v or not isinstance(v, list):
            raise ValueError("teleost_embryo must be a non-empty list")

        for sample in v:
            # Validate required fields
            if "Sample Name" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Sample Name'")
            if "Material" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Material'")
            if "Material Term Source ID" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Material Term Source ID'")
            if "Project" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Project'")
            if "Origin" not in sample:
                raise ValueError("Each teleost embryo sample must have an 'Origin'")
            if "Reproductive Strategy" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Reproductive Strategy'")
            if "Hatching" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Hatching'")
            if "Time Post Fertilisation" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Time Post Fertilisation'")
            if "Time Post Fertilisation Unit" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Time Post Fertilisation Unit'")
            if "Pre-hatching Water Temperature Average" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Pre-hatching Water Temperature Average'")
            if "Pre-hatching Water Temperature Average Unit" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Pre-hatching Water Temperature Average Unit'")
            if "Post-hatching Water Temperature Average" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Post-hatching Water Temperature Average'")
            if "Post-hatching Water Temperature Average Unit" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Post-hatching Water Temperature Average Unit'")
            if "Degree Days" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Degree Days'")
            if "Degree Days Unit" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Degree Days Unit'")
            if "Growth Media" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Growth Media'")
            if "Medium Replacement Frequency" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Medium Replacement Frequency'")
            if "Medium Replacement Frequency Unit" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Medium Replacement Frequency Unit'")
            if "Percentage Total Somite Number" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Percentage Total Somite Number'")
            if "Percentage Total Somite Number Unit" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Percentage Total Somite Number Unit'")
            if "Average Water Salinity" not in sample:
                raise ValueError("Each teleost embryo sample must have an 'Average Water Salinity'")
            if "Average Water Salinity Unit" not in sample:
                raise ValueError("Each teleost embryo sample must have an 'Average Water Salinity Unit'")
            if "Photoperiod" not in sample:
                raise ValueError("Each teleost embryo sample must have a 'Photoperiod'")

            # Validate material
            if sample["Material"] != "specimen from organism":
                raise ValueError(f"Material must be 'specimen from organism', got '{sample['Material']}'")

            # Validate project
            if sample["Project"] != "FAANG":
                raise ValueError(f"Project must be 'FAANG', got '{sample['Project']}'")

            # Validate secondary project is a list
            if "Secondary Project" in sample and not isinstance(sample["Secondary Project"], list):
                raise ValueError("Secondary Project must be a list")

            # Validate origin
            valid_origins = ["Domesticated diploid", "Domesticated Double-haploid", "Domesticated Isogenic", "Wild", "restricted access"]
            if sample["Origin"] not in valid_origins:
                raise ValueError(f"Origin must be one of {valid_origins}, got '{sample['Origin']}'")

            # Validate reproductive strategy
            valid_reproductive_strategies = ["gonochoric", "simultaneous hermaphrodite", "successive hermaphrodite", "restricted access"]
            if sample["Reproductive Strategy"] not in valid_reproductive_strategies:
                raise ValueError(f"Reproductive Strategy must be one of {valid_reproductive_strategies}, got '{sample['Reproductive Strategy']}'")

            # Validate hatching
            valid_hatching_values = ["pre", "post", "restricted access"]
            if sample["Hatching"] not in valid_hatching_values:
                raise ValueError(f"Hatching must be one of {valid_hatching_values}, got '{sample['Hatching']}'")

            # Validate time post fertilisation unit
            valid_time_units = ["hours", "days", "months", "years", "restricted access"]
            if sample["Time Post Fertilisation Unit"] not in valid_time_units:
                raise ValueError(f"Time Post Fertilisation Unit must be one of {valid_time_units}, got '{sample['Time Post Fertilisation Unit']}'")

            # Validate temperature units
            if sample["Pre-hatching Water Temperature Average Unit"] != "Degrees celsius" and sample["Pre-hatching Water Temperature Average Unit"] != "restricted access":
                raise ValueError(f"Pre-hatching Water Temperature Average Unit must be 'Degrees celsius' or 'restricted access', got '{sample['Pre-hatching Water Temperature Average Unit']}'")

            if sample["Post-hatching Water Temperature Average Unit"] != "Degrees celsius" and sample["Post-hatching Water Temperature Average Unit"] != "restricted access":
                raise ValueError(f"Post-hatching Water Temperature Average Unit must be 'Degrees celsius' or 'restricted access', got '{sample['Post-hatching Water Temperature Average Unit']}'")

            # Validate degree days unit
            if sample["Degree Days Unit"] != "Thermal time" and sample["Degree Days Unit"] != "restricted access":
                raise ValueError(f"Degree Days Unit must be 'Thermal time' or 'restricted access', got '{sample['Degree Days Unit']}'")

            # Validate growth media
            valid_growth_media = ["Water", "Growing medium", "restricted access"]
            if sample["Growth Media"] not in valid_growth_media:
                raise ValueError(f"Growth Media must be one of {valid_growth_media}, got '{sample['Growth Media']}'")

            # Validate medium replacement frequency unit
            if sample["Medium Replacement Frequency Unit"] != "days" and sample["Medium Replacement Frequency Unit"] != "restricted access":
                raise ValueError(f"Medium Replacement Frequency Unit must be 'days' or 'restricted access', got '{sample['Medium Replacement Frequency Unit']}'")

            # Validate percentage total somite number unit
            if sample["Percentage Total Somite Number Unit"] != "%" and sample["Percentage Total Somite Number Unit"] != "restricted access":
                raise ValueError(f"Percentage Total Somite Number Unit must be '%' or 'restricted access', got '{sample['Percentage Total Somite Number Unit']}'")

            # Validate average water salinity unit
            if sample["Average Water Salinity Unit"] != "parts per thousand" and sample["Average Water Salinity Unit"] != "restricted access":
                raise ValueError(f"Average Water Salinity Unit must be 'parts per thousand' or 'restricted access', got '{sample['Average Water Salinity Unit']}'")

            # Validate photoperiod format
            if sample["Photoperiod"] != "natural light" and sample["Photoperiod"] != "restricted access":
                pattern = r'^2[0-4]L|1[0-9]L|[1-9]L:2[0-4]D|1[0-9]D|[1-9]D$'
                if not re.match(pattern, sample["Photoperiod"]):
                    raise ValueError(f"Invalid photoperiod format: {sample['Photoperiod']}. Must be 'natural light', 'restricted access', or match pattern like '16L:8D'")

            # Validate generations from wild if provided
            if "Generations From Wild" in sample and sample["Generations From Wild"]:
                valid_not_applicable = ["not applicable", "not collected", "not provided", "restricted access"]
                if sample["Generations From Wild"] not in valid_not_applicable and not isinstance(sample["Generations From Wild"], (int, float)):
                    raise ValueError(f"Generations From Wild must be a number or one of {valid_not_applicable}, got '{sample['Generations From Wild']}'")

            if "Generations From Wild Unit" in sample and sample["Generations From Wild Unit"]:
                valid_units = ["generations from wild", "not applicable", "not collected", "not provided", "restricted access"]
                if sample["Generations From Wild Unit"] not in valid_units:
                    raise ValueError(f"Generations From Wild Unit must be one of {valid_units}, got '{sample['Generations From Wild Unit']}'")

        return v
