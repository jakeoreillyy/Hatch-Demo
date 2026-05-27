def rank(scored_theses: list[dict]) -> list[dict]:
    """
    Sorts scored theses by weighted_total descending.
    Adds a 'rank' field (1 = best).

    Args:
        scored_theses (list[dict]): List of thesis dicts, each containing a
            'weighted_total' field produced by the scoring module.

    Returns:
        list[dict]: The same theses sorted best-first, with a 'rank' integer
            added to each dict (1 = highest score).
    """
    sorted_theses = sorted(
        scored_theses,
        key=lambda x: x[
            "weighted_total"
        ],  # sort key: higher weighted_total = better thesis
        reverse=True,
    )

    for i, thesis in enumerate(
        sorted_theses
    ):
        thesis["rank"] = i + 1  # i is 0-based, so add 1 to make rank start at 1

    return sorted_theses


def merge_and_rank(base: list[dict], new: list[dict]) -> list[dict]:
    """
    Merges new theses into the base set and re-ranks everything.
    If a ref already exists in base, the new version replaces it.

    Args:
        base (list[dict]): The existing collection of scored and ranked theses.
        new (list[dict]): Newly scored theses to fold into the base set.

    Returns:
        list[dict]: The combined set of theses sorted and ranked from scratch.
    """
    base_by_ref = {
        t["ref"]: t for t in base
    }  # index the base list by ref for O(1) lookup

    for thesis in new:
        base_by_ref[thesis["ref"]] = (
            thesis  # overwrite any existing entry with the same ref
        )

    return rank(
        list(base_by_ref.values())
    )  # convert the dict back to a list and re-rank the full combined set
