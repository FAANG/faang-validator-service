from pydantic import ValidationError
from typing import List, Optional, Dict, Any, Tuple
import json
from organism_validator_classes import OntologyValidator

from rulesets_pydantics.organoid_ruleset import (
    FAANGOrganoidSample
)

class OrganoidValidator:
    def __init__(self, schema_file_path: str = None):
        self.ontology_validator = OntologyValidator(cache_enabled=True)
        self.schema_file_path = schema_file_path or "rulesets-json/faang_samples_organoid.metadata_rules.json"
        self._schema = None

    def validate_organoid_sample(
        self,
        data: Dict[str, Any],
        validate_ontologies: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, List[str]]]:

        errors_dict = {
            'errors': [],
            'warnings': [],
            'field_errors': {}
        }

        # Basic validation for required fields
        required_fields = [
            "Sample Name", "Material", "Material Term Source ID", "Project", 
            "Organ Model", "Organ Model Term Source ID", "Freezing Method",
            "Organoid Passage", "Organoid Passage Unit", "Organoid Passage Protocol",
            "Type Of Organoid Culture", "Growth Environment", "Derived From"
        ]

        for field in required_fields:
            if field not in data or not data[field]:
                if field not in errors_dict['field_errors']:
                    errors_dict['field_errors'][field] = []
                errors_dict['field_errors'][field].append(f"Field '{field}' is required")
                errors_dict['errors'].append(f"{field}: Field is required")

        # Conditional required fields based on freezing method
        if "Freezing Method" in data and data["Freezing Method"] and data["Freezing Method"] != "fresh":
            conditional_fields = ["Freezing Date", "Freezing Date Unit", "Freezing Protocol"]
            for field in conditional_fields:
                if field not in data or not data[field]:
                    if field not in errors_dict['field_errors']:
                        errors_dict['field_errors'][field] = []
                    errors_dict['field_errors'][field].append(f"Field '{field}' is required when Freezing Method is not 'fresh'")
                    errors_dict['errors'].append(f"{field}: Field is required when Freezing Method is not 'fresh'")

        if errors_dict['errors']:
            return None, errors_dict

        # Validate material
        if data["Material"] != "organoid":
            field = "Material"
            if field not in errors_dict['field_errors']:
                errors_dict['field_errors'][field] = []
            errors_dict['field_errors'][field].append(f"Material must be 'organoid', got '{data['Material']}'")
            errors_dict['errors'].append(f"{field}: Material must be 'organoid', got '{data['Material']}'")

        # Validate project
        if data["Project"] != "FAANG":
            field = "Project"
            if field not in errors_dict['field_errors']:
                errors_dict['field_errors'][field] = []
            errors_dict['field_errors'][field].append(f"Project must be 'FAANG', got '{data['Project']}'")
            errors_dict['errors'].append(f"{field}: Project must be 'FAANG', got '{data['Project']}'")

        # Validate lists
        list_fields = ["Secondary Project"]
        for field in list_fields:
            if field in data and data[field] and not isinstance(data[field], list):
                if field not in errors_dict['field_errors']:
                    errors_dict['field_errors'][field] = []
                errors_dict['field_errors'][field].append(f"{field} must be a list")
                errors_dict['errors'].append(f"{field}: {field} must be a list")

        # Validate freezing method
        valid_freezing_methods = [
            "ambient temperature", "cut slide", "fresh", "frozen, -70 freezer",
            "frozen, -150 freezer", "frozen, liquid nitrogen", "frozen, vapor phase",
            "paraffin block", "RNAlater, frozen", "TRIzol, frozen"
        ]
        if "Freezing Method" in data and data["Freezing Method"] and data["Freezing Method"] not in valid_freezing_methods:
            field = "Freezing Method"
            if field not in errors_dict['field_errors']:
                errors_dict['field_errors'][field] = []
            errors_dict['field_errors'][field].append(f"Invalid freezing method: '{data['Freezing Method']}'. Must be one of {valid_freezing_methods}")
            errors_dict['errors'].append(f"{field}: Invalid freezing method: '{data['Freezing Method']}'")

        # Validate growth environment
        valid_growth_environments = ["matrigel", "liquid suspension", "adherent"]
        if "Growth Environment" in data and data["Growth Environment"] and data["Growth Environment"] not in valid_growth_environments:
            field = "Growth Environment"
            if field not in errors_dict['field_errors']:
                errors_dict['field_errors'][field] = []
            errors_dict['field_errors'][field].append(f"Invalid growth environment: '{data['Growth Environment']}'. Must be one of {valid_growth_environments}")
            errors_dict['errors'].append(f"{field}: Invalid growth environment: '{data['Growth Environment']}'")

        # Validate type of organoid culture
        valid_culture_types = ["2D", "3D"]
        if "Type Of Organoid Culture" in data and data["Type Of Organoid Culture"] and data["Type Of Organoid Culture"] not in valid_culture_types:
            field = "Type Of Organoid Culture"
            if field not in errors_dict['field_errors']:
                errors_dict['field_errors'][field] = []
            errors_dict['field_errors'][field].append(f"Invalid type of organoid culture: '{data['Type Of Organoid Culture']}'. Must be one of {valid_culture_types}")
            errors_dict['errors'].append(f"{field}: Invalid type of organoid culture: '{data['Type Of Organoid Culture']}'")

        # ontology validation
        if validate_ontologies and not errors_dict['errors']:
            ontology_errors = self.validate_ontologies(data)
            errors_dict['errors'].extend(ontology_errors)

        if errors_dict['errors']:
            return None, errors_dict

        return data, errors_dict

    def validate_ontologies(self, data: Dict[str, Any]) -> List[str]:
        errors = []

        # Validate organ model term
        organ_model_term = data.get("Organ Model Term Source ID")
        if organ_model_term and organ_model_term != "restricted access":
            # Convert underscore to colon for validation
            organ_model_term_colon = organ_model_term.replace("_", ":")
            if not (organ_model_term_colon.startswith("UBERON:") or organ_model_term_colon.startswith("BTO:")):
                errors.append(f"Organ model term '{organ_model_term}' should be from UBERON or BTO ontology")

        # Validate organ part model term
        organ_part_model_term = data.get("Organ Part Model Term Source ID")
        if organ_part_model_term and organ_part_model_term != "restricted access":
            # Convert underscore to colon for validation
            organ_part_model_term_colon = organ_part_model_term.replace("_", ":")
            if not (organ_part_model_term_colon.startswith("UBERON:") or organ_part_model_term_colon.startswith("BTO:")):
                errors.append(f"Organ part model term '{organ_part_model_term}' should be from UBERON or BTO ontology")

        return errors

    def validate_with_pydantic(
        self,
        organoids: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        results = {
            'valid_organoids': [],
            'invalid_organoids': [],
            'summary': {
                'total': len(organoids),
                'valid': 0,
                'invalid': 0,
                'warnings': 0
            }
        }

        # validate organoids
        for i, org_data in enumerate(organoids):
            sample_name = org_data.get('Sample Name')

            validated_data, errors = self.validate_organoid_sample(
                org_data,
                validate_ontologies=True
            )

            if validated_data and not errors['errors']:
                results['valid_organoids'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'data': validated_data,
                    'warnings': errors['warnings']
                })
                results['summary']['valid'] += 1
                if errors['warnings']:
                    results['summary']['warnings'] += 1
            else:
                results['invalid_organoids'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'errors': errors
                })
                results['summary']['invalid'] += 1

        return results

def export_organoid_to_biosample_format(data: Dict[str, Any]) -> Dict[str, Any]:
    biosample_data = {
        "characteristics": {}
    }

    biosample_data["characteristics"]["material"] = [{
        "text": data.get("Material", ""),
        "ontologyTerms": [f"http://purl.obolibrary.org/obo/{data.get('Material Term Source ID', '').replace(':', '_')}"]
    }]

    biosample_data["characteristics"]["organ model"] = [{
        "text": data.get("Organ Model", ""),
        "ontologyTerms": [f"http://purl.obolibrary.org/obo/{data.get('Organ Model Term Source ID', '').replace(':', '_')}"]
    }]

    if "Organ Part Model" in data and data["Organ Part Model"]:
        biosample_data["characteristics"]["organ part model"] = [{
            "text": data["Organ Part Model"],
            "ontologyTerms": [f"http://purl.obolibrary.org/obo/{data.get('Organ Part Model Term Source ID', '').replace(':', '_')}"]
        }]

    if "Freezing Date" in data and data["Freezing Date"]:
        biosample_data["characteristics"]["freezing date"] = [{
            "text": data["Freezing Date"],
            "unit": data.get("Freezing Date Unit", "")
        }]

    if "Freezing Method" in data and data["Freezing Method"]:
        biosample_data["characteristics"]["freezing method"] = [{
            "text": data["Freezing Method"]
        }]

    if "Organoid Passage" in data and data["Organoid Passage"]:
        biosample_data["characteristics"]["organoid passage"] = [{
            "text": data["Organoid Passage"],
            "unit": data.get("Organoid Passage Unit", "")
        }]

    if "Growth Environment" in data and data["Growth Environment"]:
        biosample_data["characteristics"]["growth environment"] = [{
            "text": data["Growth Environment"]
        }]

    if "Type Of Organoid Culture" in data and data["Type Of Organoid Culture"]:
        biosample_data["characteristics"]["type of organoid culture"] = [{
            "text": data["Type Of Organoid Culture"]
        }]

    if "Derived From" in data and data["Derived From"]:
        biosample_data["relationships"] = [{
            "type": "derived from",
            "target": data["Derived From"]
        }]

    return biosample_data

def generate_validation_report(validation_results: Dict[str, Any]) -> str:
    report = []
    report.append("FAANG Organoid Validation Report")
    report.append("=" * 40)
    report.append(f"\nTotal organoids processed: {validation_results['summary']['total']}")
    report.append(f"Valid organoids: {validation_results['summary']['valid']}")
    report.append(f"Invalid organoids: {validation_results['summary']['invalid']}")
    report.append(f"Organoids with warnings: {validation_results['summary']['warnings']}")

    if validation_results['invalid_organoids']:
        report.append("\n\nValidation Errors:")
        report.append("-" * 20)
        for org in validation_results['invalid_organoids']:
            report.append(f"\nOrganoid: {org['sample_name']} (index: {org['index']})")
            for field, field_errors in org['errors']['field_errors'].items():
                for error in field_errors:
                    report.append(f"  ERROR in {field}: {error}")

    if validation_results['valid_organoids']:
        warnings_found = False
        for org in validation_results['valid_organoids']:
            if org.get('warnings'):
                if not warnings_found:
                    report.append("\n\nWarnings and Non-Critical Issues:")
                    report.append("-" * 30)
                    warnings_found = True

                report.append(f"\nOrganoid: {org['sample_name']} (index: {org['index']})")
                for warning in org.get('warnings', []):
                    report.append(f"  WARNING: {warning}")

    return "\n".join(report)

if __name__ == "__main__":
    json_string = """
    {
        "organoid": [

        {
            "Sample Name": "ORGANOID_SAMPLE_1",
            "Sample Description": "Test organoid sample",
            "Material": "organoid",
            "Material Term Source ID": "NCIT_C172259",
            "Project": "FAANG",
            "Secondary Project": [],
            "Availability": "",
            "Same as": "",
            "Organ Model": "liver",
            "Organ Model Term Source ID": "UBERON_0002107",
            "Organ Part Model": "",
            "Organ Part Model Term Source ID": "",
            "Freezing Date": "2023-01-15",
            "Freezing Date Unit": "YYYY-MM-DD",
            "Freezing Method": "frozen, liquid nitrogen",
            "Freezing Protocol": "http://example.com/protocol",
            "Number Of Frozen Cells": "5",
            "Number Of Frozen Cells Unit": "organoids",
            "Organoid Culture And Passage Protocol": "http://example.com/culture-protocol",
            "Organoid Passage": "3",
            "Organoid Passage Unit": "passages",
            "Organoid Passage Protocol": "http://example.com/passage-protocol",
            "Type Of Organoid Culture": "3D",
            "Organoid Morphology": "Spherical structure with central lumen",
            "Growth Environment": "matrigel",
            "Derived From": "SAMPLE_123"
        }
        ]
    }
    """

    data = json.loads(json_string)
    sample_organoids = data["organoid"]

    validator = OrganoidValidator("rulesets-json/faang_samples_organoid.metadata_rules.json")
    results = validator.validate_with_pydantic(sample_organoids)

    report = generate_validation_report(results)
    print(report)

    # export to BioSamples format
    if results['valid_organoids']:
        for valid_org in results['valid_organoids']:
            biosample_data = export_organoid_to_biosample_format(valid_org['data'])
            # print(f"\nBioSample format for {valid_org['sample_name']}:")
            # print(json.dumps(biosample_data, indent=2))
