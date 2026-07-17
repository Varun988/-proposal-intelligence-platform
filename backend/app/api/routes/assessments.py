from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.dependencies import (
    get_assessment_execution_service,
    get_assessment_service,
)
from app.core.exceptions import (
    AssessmentConflictError,
    AssessmentNotFoundError,
)
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentCreateResponse,
    AssessmentErrorResponse,
    AssessmentExecuteResponse,
    AssessmentResultsResponse,
    AssessmentStatusResponse,
)
from app.services.assessment_execution_service import AssessmentExecutionService
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["assessments"])

AssessmentServiceDependency = Annotated[
    AssessmentService,
    Depends(get_assessment_service),
]
AssessmentExecutionServiceDependency = Annotated[
    AssessmentExecutionService,
    Depends(get_assessment_execution_service),
]


@router.post(
    "",
    response_model=AssessmentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment(
    request: AssessmentCreateRequest,
    assessment_service: AssessmentServiceDependency,
) -> AssessmentCreateResponse:
    """Create a proposal assessment without executing it."""

    return await assessment_service.create_assessment(request)


@router.post(
    "/{assessment_id}/execute",
    response_model=AssessmentExecuteResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": AssessmentErrorResponse,
            "description": "Assessment not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": AssessmentErrorResponse,
            "description": "Assessment execution was already requested.",
        },
    },
)
async def execute_assessment(
    assessment_id: str,
    background_tasks: BackgroundTasks,
    execution_service: AssessmentExecutionServiceDependency,
) -> AssessmentExecuteResponse:
    """Queue one assessment for background execution."""

    try:
        response = await execution_service.request_execution(assessment_id)
    except AssessmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "assessment_not_found",
                "message": str(error),
                "assessment_id": assessment_id,
                "details": {},
            },
        ) from error
    except AssessmentConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "assessment_execution_conflict",
                "message": str(error),
                "assessment_id": assessment_id,
                "details": {},
            },
        ) from error

    background_tasks.add_task(
        execution_service.execute_assessment,
        assessment_id,
    )
    return response


@router.get(
    "/{assessment_id}/results",
    response_model=AssessmentResultsResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": AssessmentErrorResponse,
            "description": "Assessment not found.",
        },
    },
)
async def get_assessment_results(
    assessment_id: str,
    assessment_service: AssessmentServiceDependency,
) -> AssessmentResultsResponse:
    """Return available agent outputs and evaluation reports."""

    try:
        return await assessment_service.get_results(assessment_id)
    except AssessmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "assessment_not_found",
                "message": str(error),
                "assessment_id": assessment_id,
                "details": {},
            },
        ) from error


@router.get(
    "/{assessment_id}",
    response_model=AssessmentStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": AssessmentErrorResponse,
            "description": "Assessment not found.",
        },
    },
)
async def get_assessment_status(
    assessment_id: str,
    assessment_service: AssessmentServiceDependency,
) -> AssessmentStatusResponse:
    """Return the current status of one assessment."""

    try:
        return await assessment_service.get_status(assessment_id)
    except AssessmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "assessment_not_found",
                "message": str(error),
                "assessment_id": assessment_id,
                "details": {},
            },
        ) from error
