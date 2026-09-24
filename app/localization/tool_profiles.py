from datetime import date

from pydantic import HttpUrl

from app.domain.models import DomainModel, Language, NonEmptyText
from app.domain.tool_profiles import (
    CapabilityEvidence,
    EvidenceStatus,
    NetworkRequirement,
    OperationSetup,
    SetupEvidence,
    StarterGuide,
    ToolProfile,
)


class StarterStepResponse(DomainModel):
    instruction: NonEmptyText
    source_url: HttpUrl


class StarterGuideResponse(DomainModel):
    prerequisites: list[NonEmptyText]
    steps: list[StarterStepResponse]
    example: NonEmptyText
    expected_outcome: NonEmptyText
    reviewed_at: date


class SetupEvidenceResponse(DomainModel):
    property: str
    status: EvidenceStatus
    source_url: HttpUrl | None = None
    summary: NonEmptyText
    version_scope: str
    reviewed_at: date | None = None
    limitations: NonEmptyText


class OperationSetupResponse(DomainModel):
    id: str
    name: NonEmptyText
    task: NonEmptyText
    stage: str
    domain: str
    platform: NonEmptyText
    version: str | None = None
    local_components: list[NonEmptyText]
    model: NonEmptyText | None = None
    preparation_network: NetworkRequirement
    runtime_network: NetworkRequirement
    offline_features: list[NonEmptyText]
    online_only_features: list[NonEmptyText]
    hardware_requirements: NonEmptyText | None = None
    download_requirements: NonEmptyText | None = None
    offline: CapabilityEvidence
    free_plan: CapabilityEvidence
    open_source: CapabilityEvidence
    evidence_status: EvidenceStatus
    evidence: list[SetupEvidenceResponse]
    starter_guide: StarterGuideResponse


class ToolProfileResponse(DomainModel):
    offline: CapabilityEvidence
    free_plan: CapabilityEvidence
    open_source: CapabilityEvidence
    deployment: NonEmptyText
    pricing_summary: NonEmptyText
    learning_curve: NonEmptyText
    integrations: list[NonEmptyText]
    sources: list[HttpUrl]
    reviewed_at: date
    starter_guide: StarterGuideResponse
    operation_setups: list[OperationSetupResponse]


def _project_guide(guide: StarterGuide, language: Language) -> StarterGuideResponse:
    return StarterGuideResponse(
        prerequisites=[item.for_language(language) for item in guide.prerequisites],
        steps=[
            StarterStepResponse(
                instruction=step.instruction.for_language(language),
                source_url=step.source_url,
            )
            for step in guide.steps
        ],
        example=guide.example.for_language(language),
        expected_outcome=guide.expected_outcome.for_language(language),
        reviewed_at=guide.reviewed_at,
    )


def _project_evidence(
    evidence: SetupEvidence, language: Language
) -> SetupEvidenceResponse:
    return SetupEvidenceResponse(
        property=evidence.property,
        status=evidence.status,
        source_url=evidence.source_url,
        summary=evidence.summary.for_language(language),
        version_scope=evidence.version_scope,
        reviewed_at=evidence.reviewed_at,
        limitations=evidence.limitations.for_language(language),
    )


def _project_setup(
    setup: OperationSetup, language: Language
) -> OperationSetupResponse:
    return OperationSetupResponse(
        id=setup.id,
        name=setup.name.for_language(language),
        task=setup.task.for_language(language),
        stage=setup.stage,
        domain=setup.domain,
        platform=setup.platform.for_language(language),
        version=setup.version,
        local_components=[item.for_language(language) for item in setup.local_components],
        model=setup.model.for_language(language) if setup.model else None,
        preparation_network=setup.preparation_network,
        runtime_network=setup.runtime_network,
        offline_features=[item.for_language(language) for item in setup.offline_features],
        online_only_features=[item.for_language(language) for item in setup.online_only_features],
        hardware_requirements=(
            setup.hardware_requirements.for_language(language)
            if setup.hardware_requirements
            else None
        ),
        download_requirements=(
            setup.download_requirements.for_language(language)
            if setup.download_requirements
            else None
        ),
        offline=setup.offline,
        free_plan=setup.free_plan,
        open_source=setup.open_source,
        evidence_status=setup.evidence_status,
        evidence=[_project_evidence(item, language) for item in setup.evidence],
        starter_guide=_project_guide(setup.starter_guide, language),
    )


def project_profile(profile: ToolProfile | None, language: Language) -> ToolProfileResponse | None:
    if profile is None:
        return None
    return ToolProfileResponse(
        offline=profile.offline, free_plan=profile.free_plan, open_source=profile.open_source,
        deployment=profile.deployment.for_language(language),
        pricing_summary=profile.pricing_summary.for_language(language),
        learning_curve=profile.learning_curve.for_language(language),
        integrations=[item.for_language(language) for item in profile.integrations],
        sources=profile.sources, reviewed_at=profile.reviewed_at,
        starter_guide=_project_guide(profile.starter_guide, language),
        operation_setups=[
            _project_setup(setup, language) for setup in profile.operation_setups
        ],
    )
