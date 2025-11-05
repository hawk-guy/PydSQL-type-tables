"""Type introspection utilities for Pydantic models.

This module provides functions to parse and describe Pydantic BaseModel
classes and type aliases, extracting structured information about fields,
type annotations, and metadata. The output is designed to be queryable,
allowing recursive lookups of type references for DDL generation and other
schema-based operations.

Key functions:
    - retrieve_types_and_basemodels: Main entry point for extracting all
      types from a module
    - describe_annotation: Core type parser that returns structured dicts
      with "kind" classification
    - iter_model_fields: Extracts field information from Pydantic models

Note: This code has a healthy obsession with consistent dict returns.
      Every type gets a "kind" field. No exceptions. None. Zero. Zilch.
"""

from __future__ import annotations

import types
from typing import (
    Annotated,
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo

NoneType = type(None)

def is_type_annotation(obj: Any) -> bool:
    """Check for whether 'obj' looks is a type annotation.
    It does this by checking the result of get_origin.
    True for:
        get_origin constructs (Annotated/Union/Literal/Dict[List[...]...])
    """
    origin = get_origin(obj)
    return (
        origin is Annotated
        or origin is Literal
        or origin is Union
    )


def collect_base_models(
    module: types.ModuleType,
) -> dict[str, type[BaseModel]]:
    """
    Iterate over all BaseModel subclasses in a module, returning a
    mapping of name -> class.
    """
    out: dict[str, type[BaseModel]] = {}
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, BaseModel)
            and attr is not BaseModel
        ):
            out[attr_name] = attr
    return out

def find_defined_type_aliases(module: Any) -> dict[str, dict[str, Any]]:
    """Return a mapping of name -> describe_type for baseModel classes
    and type aliases defined in the module.
    """
    out: dict[str, dict[str, Any]] = {}
    for name, obj in getattr(module, "__dict__", {}).items():
        if name.startswith("_"):
            continue
        # Only keep annotation-like values
        if is_type_annotation(obj):
            out[name] = describe_annotation(obj)
    return out

def describe_annotation(tp: Any) -> dict[str, Any] | Any:
    """
    Describe a type annotation that may be a Literal, Union, or
    Annotated type. Returns a dict with 'kind' indicating the type
    category. For BaseModel classes, stores the class name as a
    reference that can be looked up. For basic types (str, int, etc.),
    stores the type name.
    """
    origin = get_origin(tp)
    args = get_args(tp)

    if origin is Literal:
        return {
            "kind": "literal",
            "values": list(args),
            "optional": False,
        }

    if origin is Union:
        # Check if NoneType is one of the union options
        # (making it optional)
        has_none = NoneType in args
        return {
            "kind": "union",
            "options": [describe_annotation(a) for a in args],
            "optional": has_none,
        }

    if origin is Annotated:
        return {
            "kind": "annotated",
            "base": describe_annotation(args[0]),
            "metadata": [describe_annotation(m) for m in args[1:]],
            "optional": False,
        }

    # Check if it's a BaseModel class - store as a reference name
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return {
            "kind": "model_ref",
            "name": tp.__name__,
            "optional": False,
        }

    # For basic types like str, int, float, bool, etc.
    if isinstance(tp, type):
        return {
            "kind": "type",
            "name": tp.__name__,
            "optional": False,
        }

    # Unknown/unhandled type annotation
    return {
        "kind": "unknown",
        "repr": str(tp),
        "optional": False,
    }

def describe_models(tp: Any) -> dict[str, Any]:
    """
    Normalize an annotation into a structured description for Pydantic
    model fields. This wraps describe_annotation and adds
    Pydantic-specific metadata like discriminator, alias, and
    description from FieldInfo.
    """
    # First, check if this is an Annotated type with FieldInfo metadata
    origin = get_origin(tp)
    args = get_args(tp)

    discriminator = None
    field_meta: dict[str, Any] = {}

    # Extract Pydantic FieldInfo metadata if present
    if origin is Annotated:
        # Check the metadata args for FieldInfo
        for meta in args[1:]:
            if isinstance(meta, FieldInfo):
                discriminator = getattr(meta, "discriminator", None)
                field_meta = {
                    "alias": getattr(meta, "alias", None),
                    "description": getattr(meta, "description", None),
                    "json_schema_extra": getattr(
                        meta, "json_schema_extra", None
                    ),
                }
                break

    # Use describe_annotation to get the base type description
    base_description = describe_annotation(tp)

    # If describe_annotation returned a dict, add Pydantic metadata
    if isinstance(base_description, dict):
        base_description["discriminator"] = discriminator
        base_description["field_meta"] = field_meta
        return base_description

    # Fallback for non-dict returns (shouldn't happen with updated
    # describe_annotation)
    return {
        "kind": "unknown",
        "repr": str(base_description),
        "optional": False,
        "discriminator": discriminator,
        "field_meta": field_meta,
    }


def iter_model_fields(
    model: type[BaseModel],
    type_aliases: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Produce a normalized view per field:
      - annotation: structured description (see describe_type)
      - required/has_default/default/alias: taken from
        model.model_fields

    If type_aliases is provided, will detect when fields use type
    aliases and return a type_ref instead of expanding them.
    """
    # Use get_type_hints to resolve string annotations to actual type
    # objects. include_extras=True preserves Annotated metadata
    hints = get_type_hints(model, include_extras=True)

    # Also get raw annotations to detect type alias names
    raw_annotations = model.__annotations__

    type_aliases = type_aliases or {}

    out: dict[str, dict[str, Any]] = {}
    for name, field in model.model_fields.items():
        ann = hints.get(name, field.annotation)

        # Check if the raw annotation is a type alias reference
        raw_ann = raw_annotations.get(name)
        if isinstance(raw_ann, str) and raw_ann in type_aliases:
            # It's a type alias reference - create a type_ref
            out[name] = {
                "annotation": {
                    "kind": "type_ref",
                    "name": raw_ann,
                    "optional": False,
                    "discriminator": None,
                    "field_meta": {},
                },
                "required": field.is_required(),
                "has_default": (
                    field.default is not None
                    or field.default_factory is not None
                ),
                "default": field.default,
                "alias": getattr(field, "alias", None),
            }
            continue

        out[name] = {
            "annotation": describe_models(ann),
            "required": field.is_required(),
            "has_default": (
                field.default is not None
                or field.default_factory is not None
            ),
            "default": field.default,
            "alias": getattr(field, "alias", None),
        }
    return out


def retrieve_types_and_basemodels(
    module: types.ModuleType,
) -> dict[str, dict[str, Any]]:
    """
    Iterate over all BaseModel subclasses in a module, returning their
    field descriptions. Also collects type aliases and annotations
    defined in the module.
    """
    out: dict[str, dict[str, Any]] = {}

    # Collect type aliases first so we can detect references to them
    type_aliases = find_defined_type_aliases(module)
    for name, description in type_aliases.items():
        out[name] = description

    # Collect BaseModel classes and their fields
    models: dict[str, type[BaseModel]] = {}
    models = collect_base_models(module)
    for name, model in models.items():
        out[name] = iter_model_fields(model, type_aliases)

    return out
