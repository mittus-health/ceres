from fastapi import APIRouter, Depends, Request

from app.api.schemas import RecommendationRequest, RecommendationResponse
from app.application.build_recommendation import BuildRecommendation

router = APIRouter()


def get_use_case(request: Request) -> BuildRecommendation:
    return request.app.state.build_recommendation


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/recommendations", response_model=RecommendationResponse)
async def recommendations(
    body: RecommendationRequest,
    use_case: BuildRecommendation = Depends(get_use_case),
) -> RecommendationResponse:
    result = await use_case.execute(body.domain_check_ins(), body.domain_forecast())
    return RecommendationResponse.model_validate(result)
