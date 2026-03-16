"""
Adapter for transforming bio.tools collector data into core models.
"""

import logging
from typing import Any

from multi_modal_maturity_model.core.models import (
    DataItem,
    EDAMItem,
    Function,
    ToolModel,
)

logger = logging.getLogger(__name__)


class BioToolsAdapter:
    """
    Transform raw bio.tools API data into ToolModel domain model.
    """

    @staticmethod
    def to_tool_model(raw_data: dict[str, Any]) -> ToolModel:
        """
        Convert raw bio.tools data to ToolModel.

        Parameters
        ----------
        raw_data : dict[str, Any]
            Raw data dictionary from BioToolsClient.fetch()

        Returns
        -------
        ToolModel
            Structured tool model.
        """
        biotools_id = raw_data.get("biotoolsID", "")
        functions = transform_functions(raw_data.get("function", []))

        return ToolModel(
            biotools_id=biotools_id,
            function=functions if functions else None,
        )


def transform_edam_terms(terms: list[dict[str, Any]]) -> list[EDAMItem]:
    """
    Transform list of EDAM term dictionaries into EDAMItem objects.
    """
    if not terms:
        return []

    result = []
    for term in terms:
        if isinstance(term, dict) and "uri" in term and "term" in term:
            result.append(EDAMItem(uri=term["uri"], term=term["term"]))

    return result


def transform_functions(functions_raw: list[dict[str, Any]]) -> list[Function]:
    """
    Transform function list from bio.tools format.
    """
    if not functions_raw:
        return []

    result = []
    for func in functions_raw:
        if not isinstance(func, dict):
            continue

        operations = transform_edam_terms(func.get("operation", []))
        inputs = transform_data_items(func.get("input", []))
        outputs = transform_data_items(func.get("output", []))

        result.append(
            Function(
                operation=operations,
                input=inputs if inputs else None,
                output=outputs if outputs else None,
            )
        )

    return result


def transform_data_items(data_list: list[dict[str, Any]]) -> list[DataItem]:
    """
    Transform input/output data item specifications.
    """
    if not data_list:
        return []

    result = []
    for item in data_list:
        if not isinstance(item, dict):
            continue

        # Extract data term (required)
        data_dict = item.get("data", {})
        if not isinstance(data_dict, dict) or "uri" not in data_dict:
            continue

        data_term = EDAMItem(uri=data_dict["uri"], term=data_dict.get("term", ""))

        # Extract format terms (optional)
        formats = transform_edam_terms(item.get("format", []))

        result.append(
            DataItem(
                data=data_term,
                format=formats if formats else None,
            )
        )

    return result
