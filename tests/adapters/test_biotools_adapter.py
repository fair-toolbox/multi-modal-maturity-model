"""
Tests for BioToolsAdapter.
"""

import pytest

from multi_modal_maturity_model.adapters.biotools_adapter import (
    BioToolsAdapter,
    transform_edam_terms,
    transform_functions,
    transform_data_items,
)
from multi_modal_maturity_model.core.models import (
    DataItem,
    EDAMItem,
    Function,
    ToolModel,
)


# ----------------------------
# Helper function tests
# ----------------------------


def test_transform_edam_terms():
    """Test transformation of EDAM terms."""
    raw = [
        {"uri": "http://edamontology.org/operation_0292", "term": "Sequence alignment"},
        {
            "uri": "http://edamontology.org/operation_0346",
            "term": "Sequence similarity search",
        },
    ]
    result = transform_edam_terms(raw)
    assert len(result) == 2
    assert result[0] == EDAMItem(
        uri="http://edamontology.org/operation_0292", term="Sequence alignment"
    )
    assert result[1] == EDAMItem(
        uri="http://edamontology.org/operation_0346", term="Sequence similarity search"
    )


def test_transform_edam_terms_empty():
    """Test transformation with empty list."""
    result = transform_edam_terms([])
    assert result == []


def test_transform_edam_terms_none():
    """Test transformation with None."""
    result = transform_edam_terms(None)
    assert result == []


def test_transform_edam_terms_missing_fields():
    """Test transformation with missing required fields."""
    raw = [
        {"uri": "http://edamontology.org/operation_0292"},  # Missing 'term'
        {"term": "Sequence alignment"},  # Missing 'uri'
        {"uri": "http://edamontology.org/operation_0346", "term": "Valid term"},
    ]
    result = transform_edam_terms(raw)
    # Only the valid entry should be included
    assert len(result) == 1
    assert result[0].uri == "http://edamontology.org/operation_0346"


def test_transform_edam_terms_invalid_type():
    """Test transformation with invalid data types."""
    raw = [
        "not a dict",
        {"uri": "http://edamontology.org/operation_0292", "term": "Valid"},
        None,
    ]
    result = transform_edam_terms(raw)
    assert len(result) == 1
    assert result[0].uri == "http://edamontology.org/operation_0292"


def test_transform_data_items():
    """Test transformation of input/output data items."""
    raw = [
        {
            "data": {"uri": "http://edamontology.org/data_0006", "term": "Data"},
            "format": [{"uri": "http://edamontology.org/format_1929", "term": "FASTA"}],
        }
    ]
    result = transform_data_items(raw)
    assert len(result) == 1
    assert result[0].data.uri == "http://edamontology.org/data_0006"
    assert result[0].data.term == "Data"
    assert len(result[0].format) == 1
    assert result[0].format[0].term == "FASTA"


def test_transform_data_items_no_format():
    """Test transformation without format field."""
    raw = [{"data": {"uri": "http://edamontology.org/data_0006", "term": "Data"}}]
    result = transform_data_items(raw)
    assert len(result) == 1
    assert result[0].data.uri == "http://edamontology.org/data_0006"
    assert result[0].format is None


def test_transform_data_items_empty():
    """Test transformation with empty list."""
    result = transform_data_items([])
    assert result == []


def test_transform_data_items_none():
    """Test transformation with None."""
    result = transform_data_items(None)
    assert result == []


def test_transform_data_items_missing_data_uri():
    """Test transformation with missing data URI."""
    raw = [
        {"data": {"term": "Data"}},  # Missing URI
        {"data": {"uri": "http://edamontology.org/data_0006", "term": "Valid Data"}},
    ]
    result = transform_data_items(raw)
    # Only valid item should be included
    assert len(result) == 1
    assert result[0].data.uri == "http://edamontology.org/data_0006"


def test_transform_data_items_invalid_type():
    """Test transformation with invalid data types."""
    raw = [
        "not a dict",
        {"data": {"uri": "http://edamontology.org/data_0006", "term": "Valid"}},
    ]
    result = transform_data_items(raw)
    assert len(result) == 1


def test_transform_functions():
    """Test transformation of function data."""
    raw = [
        {
            "operation": [
                {
                    "uri": "http://edamontology.org/operation_0292",
                    "term": "Sequence alignment",
                }
            ],
            "input": [
                {"data": {"uri": "http://edamontology.org/data_0006", "term": "Data"}}
            ],
            "output": [
                {
                    "data": {
                        "uri": "http://edamontology.org/data_0863",
                        "term": "Sequence alignment",
                    }
                }
            ],
        }
    ]
    result = transform_functions(raw)
    assert len(result) == 1
    assert len(result[0].operation) == 1
    assert result[0].operation[0].term == "Sequence alignment"
    assert len(result[0].input) == 1
    assert result[0].input[0].data.uri == "http://edamontology.org/data_0006"
    assert len(result[0].output) == 1
    assert result[0].output[0].data.uri == "http://edamontology.org/data_0863"


def test_transform_functions_minimal():
    """Test transformation with only operation field."""
    raw = [
        {
            "operation": [
                {
                    "uri": "http://edamontology.org/operation_0292",
                    "term": "Sequence alignment",
                }
            ]
        }
    ]
    result = transform_functions(raw)
    assert len(result) == 1
    assert len(result[0].operation) == 1
    assert result[0].input is None
    assert result[0].output is None


def test_transform_functions_empty():
    """Test transformation with empty list."""
    result = transform_functions([])
    assert result == []


def test_transform_functions_none():
    """Test transformation with None."""
    result = transform_functions(None)
    assert result == []


def test_transform_functions_invalid_type():
    """Test transformation with invalid data types."""
    raw = [
        "not a dict",
        {
            "operation": [
                {"uri": "http://edamontology.org/operation_0292", "term": "Valid"}
            ]
        },
    ]
    result = transform_functions(raw)
    assert len(result) == 1


# ----------------------------
# BioToolsAdapter tests
# ----------------------------


def test_to_tool_model_complete():
    """Test conversion of complete bio.tools data to ToolModel."""
    raw_data = {
        "biotoolsID": "blast",
        "function": [
            {
                "operation": [
                    {
                        "uri": "http://edamontology.org/operation_0292",
                        "term": "Sequence alignment",
                    }
                ],
                "input": [
                    {
                        "data": {
                            "uri": "http://edamontology.org/data_0006",
                            "term": "Data",
                        },
                        "format": [
                            {
                                "uri": "http://edamontology.org/format_1929",
                                "term": "FASTA",
                            }
                        ],
                    }
                ],
                "output": [
                    {
                        "data": {
                            "uri": "http://edamontology.org/data_0863",
                            "term": "Sequence alignment",
                        }
                    }
                ],
            }
        ],
    }

    result = BioToolsAdapter.to_tool_model(raw_data)

    assert isinstance(result, ToolModel)
    assert result.biotools_id == "blast"
    assert len(result.function) == 1
    assert len(result.function[0].operation) == 1
    assert result.function[0].operation[0].term == "Sequence alignment"
    assert len(result.function[0].input) == 1
    assert result.function[0].input[0].data.term == "Data"
    assert len(result.function[0].output) == 1


def test_to_tool_model_minimal():
    """Test conversion with minimal bio.tools data."""
    raw_data = {
        "biotoolsID": "minimal-tool",
    }

    result = BioToolsAdapter.to_tool_model(raw_data)

    assert isinstance(result, ToolModel)
    assert result.biotools_id == "minimal-tool"
    assert result.function is None


def test_to_tool_model_no_functions():
    """Test conversion with empty functions list."""
    raw_data = {"biotoolsID": "no-functions", "function": []}

    result = BioToolsAdapter.to_tool_model(raw_data)

    assert isinstance(result, ToolModel)
    assert result.biotools_id == "no-functions"
    assert result.function is None


def test_to_tool_model_missing_biotools_id():
    """Test conversion without biotoolsID field."""
    raw_data = {
        "function": [
            {
                "operation": [
                    {
                        "uri": "http://edamontology.org/operation_0292",
                        "term": "Sequence alignment",
                    }
                ]
            }
        ]
    }

    result = BioToolsAdapter.to_tool_model(raw_data)

    assert isinstance(result, ToolModel)
    assert result.biotools_id == ""
    assert len(result.function) == 1


def test_to_tool_model_multiple_functions():
    """Test conversion with multiple functions."""
    raw_data = {
        "biotoolsID": "multi-function-tool",
        "function": [
            {
                "operation": [
                    {
                        "uri": "http://edamontology.org/operation_0292",
                        "term": "Sequence alignment",
                    }
                ]
            },
            {
                "operation": [
                    {
                        "uri": "http://edamontology.org/operation_0346",
                        "term": "Sequence similarity search",
                    }
                ]
            },
        ],
    }

    result = BioToolsAdapter.to_tool_model(raw_data)

    assert isinstance(result, ToolModel)
    assert result.biotools_id == "multi-function-tool"
    assert len(result.function) == 2
    assert result.function[0].operation[0].term == "Sequence alignment"
    assert result.function[1].operation[0].term == "Sequence similarity search"
