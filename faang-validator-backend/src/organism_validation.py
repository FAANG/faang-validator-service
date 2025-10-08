from pydantic import ValidationError
from typing import List, Optional, Dict, Any, Tuple
import json
from src.organism_validator_classes import OntologyValidator, BreedSpeciesValidator, RelationshipValidator

from rulesets_pydantics.organism_ruleset import FAANGOrganismSample


class PydanticValidator:
    def __init__(self, schema_file_path: str = None):
        self.relationship_validator = RelationshipValidator()
        self.ontology_validator = OntologyValidator(cache_enabled=True)
        self.breed_validator = BreedSpeciesValidator(self.ontology_validator)
        self.schema_file_path = schema_file_path or "faang_samples_organism.metadata_rules.json"
        self._schema = None

    # get recommended fields from pydantic model using metadata
    def get_recommended_fields(self, model_class) -> List[str]:
        recommended_fields = []

        for field_name, field_info in model_class.model_fields.items():
            if (field_info.json_schema_extra and
                isinstance(field_info.json_schema_extra, dict) and
                field_info.json_schema_extra.get("recommended", False)):
                recommended_fields.append(field_name)

        return recommended_fields

    def validate_organism_sample(
        self,
        data: Dict[str, Any],
        validate_relationships: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[FAANGOrganismSample], Dict[str, List[str]]]:

        errors_dict = {
            'errors': [],
            'warnings': [],
            'field_errors': {}
        }

        # pydantic validation
        try:
            organism_model = FAANGOrganismSample(**data)
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(x) for x in error['loc'])
                error_msg = error['msg']

                if field_path not in errors_dict['field_errors']:
                    errors_dict['field_errors'][field_path] = []
                errors_dict['field_errors'][field_path].append(error_msg)
                errors_dict['errors'].append(f"{field_path}: {error_msg}")

            return None, errors_dict
        except Exception as e:
            errors_dict['errors'].append(str(e))
            return None, errors_dict

        # recommended fields
        recommended_fields = self.get_recommended_fields(FAANGOrganismSample)
        for field in recommended_fields:
            if getattr(organism_model, field, None) is None:
                field_info = FAANGOrganismSample.model_fields.get(field)
                field_display_name = field_info.alias if field_info and field_info.alias else field
                errors_dict['warnings'].append(
                    f"Field '{field_display_name}' is recommended but was not provided"
                )

        return organism_model, errors_dict


    def validate_with_pydantic(
        self,
        organisms: List[Dict[str, Any]],
        validate_relationships: bool = True,
    ) -> Dict[str, Any]:

        results = {
            'valid_organisms': [],
            'invalid_organisms': [],
            'summary': {
                'total': len(organisms),
                'valid': 0,
                'invalid': 0,
                'warnings': 0,
                'relationship_errors': 0
            }
        }

        # validate organisms
        for i, org_data in enumerate(organisms):
            sample_name = org_data.get('Sample Name', f'organism_{i}')

            model, errors = self.validate_organism_sample(
                org_data,
                validate_relationships=False
            )

            if model and not errors['errors']:
                results['valid_organisms'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'model': model,
                    'data': org_data,
                    'warnings': errors['warnings'],
                    'relationship_errors': []
                })
                results['summary']['valid'] += 1
                if errors['warnings']:
                    results['summary']['warnings'] += 1
            else:
                results['invalid_organisms'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'data': org_data,
                    'errors': errors
                })
                results['summary']['invalid'] += 1

        # Validate relationships between organisms
        if validate_relationships and results['valid_organisms']:
            valid_organism_data = [org['data'] for org in results['valid_organisms']]
            relationship_errors = self.relationship_validator.validate_relationships(
                valid_organism_data
            )

            # relationship errors
            for org in results['valid_organisms']:
                sample_name = org['sample_name']
                if sample_name in relationship_errors:
                    org['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

        return results


def export_organism_to_biosample_format(model: FAANGOrganismSample) -> Dict[str, Any]:

    def convert_term_to_url(term_id: str) -> str:
        if not term_id or term_id in ["restricted access", ""]:
            return ""
        if '_' in term_id and ':' not in term_id:
            term_colon = term_id.replace('_', ':', 1)
        else:
            term_colon = term_id
        return f"http://purl.obolibrary.org/obo/{term_colon.replace(':', '_')}"


    biosample_data = {
        "characteristics": {}
    }

    # material
    biosample_data["characteristics"]["material"] = [{
        "text": model.material,
        "ontologyTerms": [convert_term_to_url(model.term_source_id)]
    }]

    # organism
    biosample_data["characteristics"]["organism"] = [{
        "text": model.organism,
        "ontologyTerms": [convert_term_to_url(model.organism_term_source_id)]
    }]

    # sex
    biosample_data["characteristics"]["sex"] = [{
        "text": model.sex,
        "ontologyTerms": [convert_term_to_url(model.sex_term_source_id)]
    }]

    # birth date
    if model.birth_date and model.birth_date.strip():
        biosample_data["characteristics"]["birth date"] = [{
            "text": model.birth_date,
            "unit": model.birth_date_unit or ""
        }]

    # breed
    if model.breed and model.breed.strip():
        biosample_data["characteristics"]["breed"] = [{
            "text": model.breed,
            "ontologyTerms": [convert_term_to_url(model.breed_term_source_id)]
        }]

    # Health status (keep existing format)
    if model.health_status:
        biosample_data["characteristics"]["health status"] = []
        for status in model.health_status:
            biosample_data["characteristics"]["health status"].append({
                "text": status.text,
                "ontologyTerms": [f"http://purl.obolibrary.org/obo/{status.term.replace(':', '_')}"]
            })

    # relationships
    if model.child_of:
        biosample_data["relationships"] = []
        for parent in model.child_of:
            if parent and parent.strip():
                biosample_data["relationships"].append({
                    "type": "child of",
                    "target": parent
                })

    return biosample_data


def get_field_to_column_mapping():
    """
    Create a mapping from field names in the validation model to column names in the uploaded file.
    """
    mapping = {}
    for field_name, field_info in FAANGOrganismSample.model_fields.items():
        if field_info.alias:
            mapping[field_name] = field_info.alias

    # Add special handling for nested fields
    mapping['health_status.text'] = 'Health Status'
    mapping['health_status.term'] = 'Health Status Term Source ID'

    return mapping


def process_validation_errors(invalid_organisms, sheet_name):
    """
    Process validation errors and create a structured format for display.

    Args:
        invalid_organisms (list): List of invalid organisms with their errors
        sheet_name (str): Name of the sheet from which data was extracted

    Returns:
        list: List of dictionaries containing error information
    """
    error_data = []
    field_to_column = get_field_to_column_mapping()

    for org in invalid_organisms:
        sample_name = org['sample_name']
        field_errors = org['errors'].get('field_errors', {})
        for field, errors in field_errors.items():
            # Map field name to column name
            # Handle complex field paths (e.g., health_status.0.text)
            field_parts = field.split('.')

            # Try exact match first
            column_name = field_to_column.get(field, None)

            # If no exact match, try to match the base field
            if column_name is None and len(field_parts) > 1:
                # Check if it's an array index pattern (e.g., health_status.0.text)
                if len(field_parts) > 2 and field_parts[1].isdigit():
                    # Try to match without the index (e.g., health_status.text)
                    base_field = f"{field_parts[0]}.{field_parts[2]}"
                    column_name = field_to_column.get(base_field, None)

                # If still no match, try just the base field
                if column_name is None:
                    base_field = field_parts[0]
                    column_name = field_to_column.get(base_field, field)

            # If still no match, use the original field name
            if column_name is None:
                column_name = field

            error_data.append({
                'Sheet': sheet_name,  # Use the actual sheet name from the uploaded file
                'Sample Name': sample_name,
                'Column Name': column_name,
                'Error': '; '.join(errors)
            })

    return error_data


def generate_validation_report(validation_results: Dict[str, Any]) -> str:
    report = []
    report.append("FAANG Organism Validation Report")
    report.append("=" * 40)
    report.append(f"\nTotal organisms processed: {validation_results['summary']['total']}")
    report.append(f"Valid organisms: {validation_results['summary']['valid']}")
    report.append(f"Invalid organisms: {validation_results['summary']['invalid']}")

    # If all records are valid, just show a simple message
    if validation_results['summary']['invalid'] == 0:
        report.append("\nAll records are valid.")
        return "\n".join(report)

    # Only show errors for invalid organisms
    # if validation_results['invalid_organisms']:
    #     report.append("\n\nErrors:")
    #     report.append("-" * 20)
    #     for org in validation_results['invalid_organisms']:
    #         report.append(f"\nOrganism: {org['sample_name']} (index: {org['index']})")
    #         for field, field_errors in org['errors'].get('field_errors', {}).items():
    #             for error in field_errors:
    #                 report.append(f"  ERROR in {field}: {error}")
    #         for error in org['errors'].get('errors', []):
    #             if not any(error.startswith(field) for field in org['errors'].get('field_errors', {})):
    #                 report.append(f"  ERROR: {error}")

    return "\n".join(report)


# if __name__ == "__main__":
#     # Test with the new JSON format
#     json_string = """
#      {
#          "organism": [
#              {
#                  "Sample Name": "ECA_UKY_H11",
#                  "Sample Description": "Foal",
#                  "Material": "organism",
#                  "Term Source ID": "OBI_0100026",
#                  "Project": "FAANG",
#                  "Secondary Project": "AQUA-FAANG",
#                  "Availability": "",
#                  "Same as": "",
#                  "Organism": "Equus caballus",
#                  "Organism Term Source ID": "NCBITaxon:333920",
#                  "Sex": "male",
#                  "Sex Term Source ID": "PATO_0000384",
#                  "Birth Date": "2013-02",
#                  "Unit": "YYYY-MM",
#                  "Health Status": [
#                      {
#                          "text": "normal",
#                          "term": "PATO:0000461"
#                      }
#                  ],
#                  "Diet": "",
#                  "Birth Location": "",
#                  "Birth Location Latitude": "",
#                  "Birth Location Latitude Unit": "",
#                  "Birth Location Longitude": "",
#                  "Birth Location Longitude Unit": "",
#                  "Birth Weight": "",
#                  "Birth Weight Unit": "",
#                  "Placental Weight": "",
#                  "Placental Weight Unit": "",
#                  "Pregnancy Length": "",
#                  "Pregnancy Length Unit": "",
#                  "Delivery Timing": "",
#                  "Delivery Ease": "",
#                  "Child Of": ["", ""],
#                  "Pedigree": ""
#              },
#             {
#                  "Sample Name": "ECA_UKY_H1",
#                  "Sample Description": "Foal, 9 days old, Thoroughbred",
#                  "Material": "organism",
#                  "Term Source ID": "OBI_0100026",
#                  "Project": "FAANG",
#                  "Secondary Project": "AQUA-FAANG",
#                  "Availability": "",
#                  "Same as": "",
#                  "Organism": "Equus caballus",
#                  "Organism Term Source ID": "NCBITaxon:3037151",
#                  "Sex": "female",
#                  "Sex Term Source ID": "PATO_0000383",
#                  "Birth Date": "014-07",
#                  "Unit": "YYYY-MM",
#                  "Health Status": [
#                      {
#                          "text": "normal",
#                          "term": "PATO:0000461"
#                      }
#                  ],
#                  "Diet": "",
#                  "Birth Location": "",
#                  "Birth Location Latitude": "",
#                  "Birth Location Latitude Unit": "",
#                  "Birth Location Longitude": "",
#                  "Birth Location Longitude Unit": "",
#                  "Birth Weight": "",
#                  "Birth Weight Unit": "",
#                  "Placental Weight": "",
#                  "Placental Weight Unit": "",
#                  "Pregnancy Length": "",
#                  "Pregnancy Length Unit": "",
#                  "Delivery Timing": "",
#                  "Delivery Ease": "",
#                  "Child Of": ["aaa", ""],
#                  "Pedigree": ""
#              }
#          ]
#      }
#      """
#
#     data = json.loads(json_string)
#     sample_organisms = data.get("organism", [])
#
#     validator = PydanticValidator()
#     results = validator.validate_with_pydantic(sample_organisms)
#
#     report = generate_validation_report(results)
#     print(report)
#
#     # Export to BioSamples format if valid
#     if results['valid_organisms']:
#         for valid_org in results['valid_organisms']:
#             biosample_data = export_organism_to_biosample_format(valid_org['model'])
#             print(f"\nBioSample format for {valid_org['sample_name']}:")
#             print(json.dumps(biosample_data, indent=2))
