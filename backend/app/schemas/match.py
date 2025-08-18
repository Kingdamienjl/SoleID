from pydantic import BaseModel
from typing import List
from app.schemas.shoe import Shoe


class Candidate(BaseModel):
    score: float
    shoe: Shoe


class MatchResponse(BaseModel):
    candidates: List[Candidate]
