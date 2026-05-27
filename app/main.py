from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)  # allows the frontend to call the API
from fastapi.staticfiles import StaticFiles

from app.data_load import (
    load_theses,
    load_theses_from_bytes,
)
from app.scoring import score_theses
from app.ranking import (
    rank,
    merge_and_rank,
)

app = FastAPI(
    title="Hatch105 Ranking System"
)  # create the FastAPI app

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # allows requests
    allow_methods=["*"],  # allow all http methods
    allow_headers=["*"],  # allow all request headers
)

# holds the current ranked list in memory.
# seeded from the base 50 on startup.
_ranked: list[dict] = (
    []
)  # stores live rankings across requests


@app.on_event("startup")
async def startup():
    """
    Scores and ranks the base 50 theses when the server starts.
    Uses cache so no API calls after the first run.
    """
    global _ranked
    print(
        "Loading base theses..."
    )
    base = load_theses(
        "data/candidate_theses.json"
    )  # read the previously ranked theses from disk
    scored = score_theses(base)
    _ranked = rank(scored)
    print(
        f"Ready — {len(_ranked)} theses ranked."
    )


@app.get("/theses")
def get_theses():
    """
    Returns the current full ranked list.

    Returns:
        list[dict]: All theses in ranked order, each including scores and metadata.
    """
    return _ranked


@app.post("/rank")
async def rank_new(file: UploadFile = File(...)):
    """
    Accepts a CSV or JSON file of new theses.
    Scores them, merges into the existing ranked set, returns the full updated list.

    Args:
        file (UploadFile): Uploaded .csv or .json file containing new thesis records.

    Returns:
        list[dict]: The full updated ranked list including both existing and new theses.

    Raises:
        HTTPException: 400 if the file extension is not .csv or .json.
        HTTPException: 422 if the file content cannot be parsed.
    """
    global _ranked

    filename = (
        file.filename
    )
    if not filename.endswith(
        (".csv", ".json")
    ):
        raise HTTPException(
            status_code=400, detail="File must be .csv or .json"
        )

    content = await file.read()

    try:
        new_theses = load_theses_from_bytes(
            content, filename
        )  # go through uploaded bytes into thesis dicts
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Failed to parse file: {e}"
        )

    print(
        f"Scoring {len(new_theses)} new theses..."
    )  # Log how many theses are about to be scored
    scored_new = score_theses(new_theses)
    _ranked = merge_and_rank(
        _ranked, scored_new
    )  # merge new theses into the existing set and re-rank

    return _ranked  # updated ranked list


# serve the frontend
app.mount(
    "/", StaticFiles(directory="frontend", html=True), name="frontend"
)
