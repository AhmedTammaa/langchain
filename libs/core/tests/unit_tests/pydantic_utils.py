from typing import Any, Type

from pydantic import BaseModel


# Function to replace allOf with $ref
def replace_all_of_with_ref(schema: Any) -> None:
    if isinstance(schema, dict):
        # If the schema has an allOf key with a single item that contains a $ref
        if (
            "allOf" in schema
            and len(schema["allOf"]) == 1
            and "$ref" in schema["allOf"][0]
        ):
            schema["$ref"] = schema["allOf"][0]["$ref"]
            del schema["allOf"]
            if "default" in schema and schema["default"] is None:
                del schema["default"]
        else:
            # Recursively process nested schemas
            for key, value in schema.items():
                if isinstance(value, (dict, list)):
                    replace_all_of_with_ref(value)
    elif isinstance(schema, list):
        for item in schema:
            replace_all_of_with_ref(item)


def remove_all_none_default(schema: Any) -> None:
    """Removing all none defaults.

    Pydantic v1 did not generate these, but Pydantic v2 does.

    The None defaults usually represent **NotRequired** fields, and the None value
    is actually **incorrect** as a value since the fields do not allow a None value.

    See difference between Optional and NotRequired types in python.
    """
    if isinstance(schema, dict):
        for key, value in schema.items():
            if isinstance(value, dict):
                if "default" in value and value["default"] is None:
                    any_of = value.get("anyOf", [])
                    for type_ in any_of:
                        if "type" in type_ and type_["type"] == "null":
                            break  # Null type explicitly defined
                    else:
                        del value["default"]
                remove_all_none_default(value)
            elif isinstance(value, list):
                for item in value:
                    remove_all_none_default(item)
    elif isinstance(schema, list):
        for item in schema:
            remove_all_none_default(item)


def _schema(obj: Type[BaseModel]) -> dict:
    """Return the schema of the object."""
    # Remap to old style schema
    if not hasattr(obj, "model_json_schema"):  # V1 model
        return obj.schema()

    schema_ = obj.model_json_schema(ref_template="#/definitions/{model}")
    if "$defs" in schema_:
        schema_["definitions"] = schema_["$defs"]
        del schema_["$defs"]

    replace_all_of_with_ref(schema_)
    remove_all_none_default(schema_)

    return schema_