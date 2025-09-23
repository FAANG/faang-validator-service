from pydantic import BaseModel, Field, field_validator
from src.organism_validator_classes import BreedSpeciesValidator, OntologyValidator
from typing import List, Optional, Union, Literal
import re

from .standard_ruleset import SampleCoreMetadata

class HealthStatus(BaseModel):
    text: str
    ontology_name: Optional[Literal["PATO", "EFO"]] = None
    term: Union[str, Literal["not applicable", "not collected", "not provided", "restricted access"]]

    @field_validator('term')
    def validate_health_status(cls, v, info):
        if v in ["not applicable", "not collected", "not provided", "restricted access"]:
            return v

        # determine which ontology to use (PATO or EFO)
        ov = OntologyValidator(cache_enabled=True)
        values = info.data
        ont = values.get('ontology_name', "PATO")
        res = ov.validate_ontology_term(
            term=v,
            ontology_name=ont,
            allowed_classes=["PATO:0000461", "EFO:0000408"]
        )
        if res.errors:
            raise ValueError(f"HealthStatus term invalid: {res.errors}")

        return v

class FAANGOrganismSample(SampleCoreMetadata):
    # required fields
    sample_name: str = Field(..., alias="Sample Name")
    organism: str = Field(..., alias="Organism")
    organism_term_source_id: Union[str, Literal["restricted access"]] = Field(..., alias="Organism Term Source ID")
    sex: str = Field(..., alias="Sex")
    sex_term_source_id: Union[str, Literal["restricted access"]] = Field(..., alias="Sex Term Source ID")

    # recommended fields
    birth_date: Optional[str] = Field(None, alias="Birth Date", json_schema_extra={"recommended": True})
    birth_date_unit: Optional[Literal[
        "YYYY-MM-DD",
        "YYYY-MM",
        "YYYY",
        "not applicable",
        "not collected",
        "not provided",
        "restricted access",
        ""
    ]] = Field(None, alias="Unit", json_schema_extra={"recommended": True})
    breed: Optional[str] = Field(None, alias="Breed", json_schema_extra={"recommended": True})
    breed_term_source_id: Optional[Union[str, Literal["not applicable", "restricted access", ""]]] = Field(None,
                                                                                                           alias="Breed Term Source ID",
                                                                                                           json_schema_extra={"recommended": True})

    health_status: Optional[List[HealthStatus]] = Field(None,
                                                        alias="Health Status",
                                                        description="Healthy animals should have the term normal, "
                                                                    "otherwise use the as many disease terms as "
                                                                    "necessary from EFO.",
                                                        json_schema_extra={"recommended": True})
    # Optional fields - numeric fields
    diet: Optional[str] = Field(None, alias="Diet")
    birth_location: Optional[str] = Field(None, alias="Birth Location")

    birth_location_latitude: Optional[float] = Field(None, alias="Birth Location Latitude")
    birth_location_latitude_unit: Optional[Literal["decimal degrees"]] = Field(None,
                                                                                   alias="Birth Location Latitude Unit")
    birth_location_longitude: Optional[float] = Field(None, alias="Birth Location Longitude")
    birth_location_longitude_unit: Optional[Literal["decimal degrees"]] = Field(None,
                                                                                    alias="Birth Location Longitude Unit")
    birth_weight: Optional[float] = Field(None, alias="Birth Weight")
    birth_weight_unit: Optional[Literal["kilograms", "grams"]] = Field(None, alias="Birth Weight Unit")

    placental_weight: Optional[float] = Field(None, alias="Placental Weight")
    placental_weight_unit: Optional[Literal["kilograms", "grams"]] = Field(None, alias="Placental Weight Unit")

    pregnancy_length: Optional[float] = Field(None, alias="Pregnancy Length")
    pregnancy_length_unit: Optional[Literal["days", "weeks", "months", "day", "week", "month", ""]] = Field(None,
                                                                                                            alias="Pregnancy Length Unit")
    delivery_timing: Optional[Literal[
        "early parturition",
        "full-term parturition",
        "delayed parturition"
    ]] = Field(None, alias="Delivery Timing")

    delivery_ease: Optional[Literal[
        "normal autonomous delivery",
        "c-section",
        "veterinarian assisted"
    ]] = Field(None, alias="Delivery Ease")

    child_of: Optional[List[str]] = Field(None, alias="Child Of")
    pedigree: Optional[str] = Field(None,
                                    alias="Pedigree")
    # sample_name: Optional[str] = Field(None, alias="Sample Name")


    @field_validator('sample_name')
    def validate_sample_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Sample Name is required and cannot be empty")
        return v.strip()

    @field_validator('organism_term_source_id')
    def validate_organism_term(cls, v, info):
        if v == "restricted access":
            return v

        # convert underscore to colon
        term_with_colon = v.replace('_', ':', 1)

        if not term_with_colon.startswith("NCBITaxon:"):
            raise ValueError(f"Organism term '{v}' should be from NCBITaxon ontology")

        # ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name="NCBITaxon",
            allowed_classes=["NCBITaxon"]
        )
        if res.errors:
            raise ValueError(f"Organism term invalid: {res.errors}")

        return v

    @field_validator('sex_term_source_id')
    def validate_sex_term(cls, v, info):
        if v == "restricted access":
            return v

        # convert underscore to colon
        term_with_colon = v.replace('_', ':', 1)

        if not term_with_colon.startswith("PATO:"):
            raise ValueError(f"Sex term '{v}' should be from PATO ontology")

        # ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name="PATO",
            allowed_classes=["PATO:0000047"]
        )
        if res.errors:
            raise ValueError(f"Sex term invalid: {res.errors}")

        return v

    @field_validator('breed_term_source_id')
    def validate_breed_term(cls, v, info):
        if not v or v in ["not applicable", "restricted access", ""]:
            return v

        # convert underscore to colon
        term_with_colon = v.replace('_', ':', 1)

        if not term_with_colon.startswith("LBO:"):
            raise ValueError(f"Breed term '{v}' should be from LBO ontology")

        # ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name="LBO",
            allowed_classes=["LBO"]
        )
        if res.errors:
            raise ValueError(f"Breed term invalid: {res.errors}")

        # breed-species compatibility validation
        values = info.data
        breed_text = values.get('Breed') or values.get('breed')
        organism_text = values.get('Organism') or values.get('organism')
        organism_term = values.get('Organism Term Source ID') or values.get('organism_term_source_id')

        if breed_text and breed_text.strip() and organism_text and organism_text.strip():
            try:
                def convert_term(term_id: str) -> str:
                    if not term_id or term_id in ["restricted access", "not applicable", "not collected",
                                                  "not provided"]:
                        return term_id
                    if '_' in term_id and ':' not in term_id:
                        return term_id.replace('_', ':', 1)
                    return term_id

                breed_validator = BreedSpeciesValidator(ov)  # Reuse the existing ontology validator
                organism_term_colon = convert_term(organism_term)
                breed_term_colon = convert_term(v)

                breed_errors = breed_validator.validate_breed_for_species(
                    organism_term_colon, breed_term_colon
                )
                if breed_errors:
                    raise ValueError(f"Breed '{breed_text}' is not compatible with species '{organism_text}'")

            except Exception as e:
                if "not compatible" in str(e):
                    raise  # Re-raise compatibility errors as-is
                raise ValueError(f"Error validating breed-species compatibility: {str(e)}")

        return v


    @field_validator('breed')
    def validate_breed_consistency(cls, v, info):
        values = info.data
        breed_term = values.get('Breed Term Source ID') or values.get('breed_term_source_id')

        # check if breed is provided without breed_term_source_id
        if v and v.strip() and not breed_term:
            raise ValueError(f"Breed '{v}' is provided but Breed Term Source ID is missing")

        #check if breed_term_source_id is provided without breed text
        if (breed_term and
            breed_term not in ["", "not applicable", "restricted access"] and
            (not v or not v.strip())):
            raise ValueError("Breed Term Source ID is provided but Breed text is missing")

        return v

    @field_validator('birth_date')
    def validate_birth_date_format(cls, v, info):
        if not v or v in ["not applicable", "not collected", "not provided", "restricted access", ""]:
            return v

        values = info.data
        unit = values.get('Unit') or values.get('birth_date_unit')

        if unit == "YYYY-MM-DD":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
        elif unit == "YYYY-MM":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])$'
        elif unit == "YYYY":
            pattern = r'^[12]\d{3}$'
        else:
            return v

        if not re.match(pattern, v):
            raise ValueError(f"Invalid birth date format: {v}. Must match {unit} pattern")

        return v

    @field_validator('birth_location_latitude', mode='before')
    def validate_latitude(cls, v):
        if not v or v.strip() == "":
            return None

        try:
            lat_val = float(v)
            if not (-90 <= lat_val <= 90):
                raise ValueError(f"Latitude must be between -90 and 90 degrees, got {lat_val}")
        except ValueError as e:
            if "could not convert" in str(e):
                raise ValueError(f"Latitude must be a valid number, got '{v}'")
            raise

        return v

    @field_validator('birth_location_longitude', mode='before')
    def validate_longitude(cls, v):
        if not v or v.strip() == "":
            return None

        try:
            lon_val = float(v)
            if not (-180 <= lon_val <= 180):
                raise ValueError(f"Longitude must be between -180 and 180 degrees, got {lon_val}")
        except ValueError as e:
            if "could not convert" in str(e):
                raise ValueError(f"Longitude must be a valid number, got '{v}'")
            raise

        return v

    @field_validator('birth_weight', 'placental_weight', 'pregnancy_length', mode='before')
    def validate_numeric_fields(cls, v):
        if not v or v.strip() == "":
            return None

        try:
            float(v)
        except ValueError:
            raise ValueError(f"Value must be a valid number, got '{v}'")

        return v

    @field_validator('child_of')
    def validate_child_of(cls, v):
        if v is None:
            return None

        # filter empty strings and None
        cleaned = [item.strip() for item in v if item and item.strip()]

        if len(cleaned) > 2:
            raise ValueError("Organism can have at most 2 parents")

        return cleaned if cleaned else None

    @field_validator('pedigree')
    def validate_pedigree_url(cls, v):
        if not v or v.strip() == "":
            return v

        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Pedigree must be a valid URL starting with http:// or https://")

        return v

    # Helper method to convert empty strings to None for optional fields
    @field_validator(
        'birth_date_unit', 'birth_location_latitude_unit', 'birth_location_longitude_unit',
        'birth_weight_unit', 'placental_weight_unit', 'pregnancy_length_unit',
        'delivery_timing', 'delivery_ease', 'diet', 'birth_location',
        'birth_location_latitude', 'birth_location_longitude', 'birth_weight',
        'placental_weight', 'pregnancy_length', 'pedigree', 'breed_term_source_id', mode='before'
    )
    def convert_empty_strings_to_none(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"