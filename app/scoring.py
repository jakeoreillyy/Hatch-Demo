import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # reads .env file and injects variables into os.environ

client = (
    Anthropic()
)  # create anthropic API app

CACHE_PATH = Path(
    "data/ranked_candidates.json"
)  # path where scored results are stored between runs

SCORING_PROMPT = Path("scoring_prompt.txt").read_text(
    encoding="utf-8"
)  # loads the system prompt that tells Claude how to score a thesis

WEIGHTS = {
    "buildability": 2,  # Most important: 10-week constraint to build
    "speed_to_revenue": 2,  # Equally important: 10-week revenue genrated
    "distribution": 1.5,  # Shopify App Store is an advantage
    "defensibility": 1,  # Can someone make there own over night
    "market_size": 1.5,  # Room for growth to €1M+
}


def _load_cache() -> dict:
    """
    Loads the scoring cache from disk if it exists.

    Returns:
        dict: Cached scoring data keyed by thesis ref, or an empty dict
            if no cache file exists.
    """
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)  # return JSON as dict
    return {}  # return empty is there is no cache


def _save_cache(cache: dict) -> None:
    """
    Persists the scoring cache to disk.

    Args:
        cache (dict): The full scoring cache to write, keyed by thesis ref.
    """
    CACHE_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )
    with open(
        CACHE_PATH, "w", encoding="utf-8"
    ) as f:
        json.dump(cache, f, indent=2)  # Write the cache dict as JSON


def _weighted_total(scores: dict) -> float:
    """
    Calculates the weighted total score for a thesis.

    Args:
        scores (dict): Raw dimension scores keyed by dimension name
            (e.g. 'buildability').

    Returns:
        float: Sum of each dimension score multiplied by its weight from WEIGHTS.
    """
    return sum(
        scores[k] * WEIGHTS[k] for k in WEIGHTS
    )  # multiply each score by its weight and sum the results


def _score_one(thesis: dict) -> dict:
    """
    Sends one thesis to Claude Haiku and returns parsed scores + rationale.
    Falls back to neutral scores if the API response can't be parsed.

    Args:
        thesis (dict): A single thesis record containing ref, title, one_liner,
            example_customer, and wedge fields.

    Returns:
        dict: Scoring result with keys buildability, speed_to_revenue, distribution,
            defensibility, market_size, weighted_total, and rationale.
    """
    user_message = (
        f"ref: {thesis['ref']}\n"  # unique identifier
        f"title: {thesis['title']}\n"  # human readable name
        f"one_liner: {thesis['one_liner']}\n"  # one sentence pitch
        f"example_customer: {thesis['example_customer']}\n"  # who the first customer is
        f"wedge: {thesis['wedge']}"  # problem being solved first
    )  # formats to plain text so model can read

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # fast + cheap, good for a prototype
            max_tokens=400,  # limit to 400 tokens
            temperature=0,  # keeps output similar across runs
            system=SCORING_PROMPT,  # load the scoring criteria
            messages=[
                {"role": "user", "content": user_message}
            ],  # turn requst into theses data
        )

        raw = response.content[
            0
        ].text.strip()  # extract text and trim whitespace

        if raw.startswith("```"): 
            raw = (
                raw.split("```")[1].removeprefix("json").strip()
            )  # strip fence and json tag

        scores = json.loads(raw)  # load the cleaned sting into a dict

        # returns review
        return {
            "buildability": scores[
                "buildability"
            ],  # how feasable 
            "speed_to_revenue": scores[
                "speed_to_revenue"
            ],  # how quickly it can start generating revenue
            "distribution": scores["distribution"],  # how easy it is to reach customers
            "defensibility": scores[
                "defensibility"
            ],  # how hard it is for competitors to copy
            "market_size": scores["market_size"],  # potential total addressable market
            "weighted_total": _weighted_total(
                scores
            ),  # total score applying dimension weights
            "rationale": scores[
                "rationale"
            ],  # claudes brief justification for the scores
        }

    except Exception as e:
        print(
            f"Warning: scoring failed for {thesis['ref']}: {e}. Using neutral fallback."
        )
        neutral = {
            k: 3 for k in WEIGHTS
        }  # Aassign a mid-point score of 3 to every dimension
        return {
            **neutral,  # spread the neutral scores into the return dict
            "weighted_total": _weighted_total(
                neutral
            ),  # calculate the weighted total for the neutral scores
            "rationale": "Scoring unavailable: manual review required.",  # flag that this entry needs a human check
        }


def score_theses(theses: list[dict], force_rescore: bool = False) -> list[dict]:
    """
    Scores a list of theses. Skips any already in cache unless force_rescore=True.
    Returns the full list with scores attached.

    Args:
        theses (list[dict]): List of thesis records to score.
        force_rescore (bool): If True, bypasses the cache and re-scores every
            thesis via the API. Defaults to False.

    Returns:
        list[dict]: The input theses list with scoring fields merged in,
            in the same order.
    """
    cache = _load_cache()
    scored = []  # will accumulate the fully scored thesis dicts

    for thesis in theses:
        ref = thesis["ref"]

        company_name = thesis.get(
            "company_name", ""
        )

        if ref in cache and not force_rescore:
            print(
                f"  {ref} — loaded from cache"
            )
            cache[ref] = {
                "company_name": company_name,
                **{k: v for k, v in cache[ref].items() if k != "company_name"},
            }  # refresh company_name in cache with the latest value from input
        else:
            print(
                f"  {ref} — scoring via API..."
            ) 
            score_data = _score_one(thesis)  # call claude to score this thesis
            cache[ref] = {
                "company_name": company_name,
                **score_data,
            }  # Sstore the fresh scores in the cache dict

        result = {
            **cache[ref],
            **thesis,
        }  # merge cache entry with the original thesis, letting thesis fields override stale cache values
        scored.append(result)  # add the fully merged record to the results list

    _save_cache(
        cache
    )  # skip already scored theses
    return scored
