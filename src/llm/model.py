from pydantic import BaseModel


class RaterResponse(BaseModel):
    match_score: int
    likelihood_score: int
    match_reason: str
    likelihood_reason: str
