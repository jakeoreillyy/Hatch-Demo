import csv  # parsie CSV
import json  # parse JSON
from pathlib import Path  # path manipulation


def _parse(text: str, suffix: str) -> list[dict]:
    """
    Parses raw file text into a list of thesis dicts based on the file extension.

    Args:
        text (str): The full file content as a string.
        suffix (str): The file extension including the dot, e.g. '.json' or '.csv'.

    Returns:
        list[dict]: Normalised list of thesis records.

    Raises:
        ValueError: If the file is not '.json' or '.csv'.
    """
    if suffix == ".json":
        data = json.loads(
            text
        )  # convert the JSON into a list of dicts
    elif suffix == ".csv":
        data = list(
            csv.DictReader(text.splitlines())
        )  # convert the CSV into a list of dicts, uses the header as keys
    else:
        raise ValueError(
            f"Unsupported file type: {suffix}. Use .csv or .json"
        )  # error handling for different file types
    return _normalise(
        data
    )


def load_theses(filepath: str) -> list[dict]:
    """
    Loads and parses a thesis file from disk by path.

    Args:
        filepath (str): Absolute or relative path to a .csv or .json file.

    Returns:
        list[dict]: Normalised list of thesis records.

    Raises:
        FileNotFoundError: If the file does not exist at the given path.
        ValueError: If the file extension is not supported.
    """
    path = Path(
        filepath
    )  # Wrap the string path in a Path object for cross-platform handling
    if not path.exists():  # Guard against typos or missing files before trying to read
        raise FileNotFoundError(
            f"File not found: {filepath}"
        )  # Surface a clear error instead of a cryptic OS error
    return _parse(
        path.read_text(encoding="utf-8"), path.suffix
    )  # Read the whole file and hand off to _parse


def load_theses_from_bytes(content: bytes, filename: str) -> list[dict]:
    """
    Loads and parses a thesis file from an in-memory byte string (e.g. an HTTP upload).

    Args:
        content (bytes): Raw file bytes, typically from an uploaded file.
        filename (str): Original filename, used only to determine the file extension.

    Returns:
        list[dict]: Normalised list of thesis records.

    Raises:
        ValueError: If the file extension is not supported.
    """
    return _parse(
        content.decode("utf-8"), Path(filename).suffix
    )  # parse and decode the file


def _normalise(data: list[dict]) -> list[dict]:
    """
    Strips whitespace from all values and enforces the expected keys.
    Raises clearly if a required field is missing.

    Args:
        data (list[dict]): Raw list of row dicts as parsed from JSON or CSV.

    Returns:
        list[dict]: Cleaned list containing only the canonical thesis fields.

    Raises:
        ValueError: If any row is missing one or more required fields.
    """
    required = {
        "ref",
        "title",
        "one_liner",
        "example_customer",
        "wedge",
    }  # each theses must have these keys

    normalised = []
    for row in data:  # process each row individually
        # strip whitespace
        row = {
            k: v.strip() if isinstance(v, str) else v for k, v in row.items()
        } 

        missing = required - set(
            row.keys()
        )  # find fields that are absent
        if missing:
            raise ValueError(
                f"Row missing fields: {missing}. Row: {row}"
            )  # raise error if there are missing fields

        normalised.append(
            {
                "ref": row["ref"],  # unique identifier for the thesis
                "company_name": row.get("company_name")
                or row.get(
                    "title", ""
                ),  # use company_name if present, fall back to title, then empty string
                "title": row["title"],  # short name for the idea
                "one_liner": row[
                    "one_liner"
                ],  # description of the business
                "example_customer": row[
                    "example_customer"
                ],  # target customer
                "wedge": row[
                    "wedge"
                ],  # problem the product solves
            }
        )

    return normalised  # return the dict
