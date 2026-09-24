"""Evidence-backed comparison and onboarding content shared by API and catalog."""
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, HttpUrl, StringConstraints, model_validator

from app.domain.base import DomainModel, LocalizedText


class CapabilityEvidence(DomainModel):
    value: bool | None = None
    source_url: HttpUrl | None = None
    reviewed_at: date | None = None

    @model_validator(mode="after")
    def require_evidence_for_known_value(self) -> Self:
        if self.value is not None and (self.source_url is None or self.reviewed_at is None):
            raise ValueError("known capability requires source_url and reviewed_at")
        return self


class EvidenceStatus(StrEnum):
    OFFICIAL_DOCUMENTATION = "official_documentation"
    INDEPENDENT_TEST = "independent_test"
    UNDOCUMENTED = "undocumented"
    CONFLICTING = "conflicting"


class NetworkRequirement(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    OPTIONAL = "optional"
    UNKNOWN = "unknown"


SetupIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class SetupEvidence(DomainModel):
    property: SetupIdentifier
    status: EvidenceStatus
    source_url: HttpUrl | None = None
    summary: LocalizedText
    version_scope: SetupIdentifier
    reviewed_at: date | None = None
    limitations: LocalizedText

    @model_validator(mode="after")
    def require_source_for_documented_status(self) -> Self:
        if self.status is not EvidenceStatus.UNDOCUMENTED and (
            self.source_url is None or self.reviewed_at is None
        ):
            raise ValueError("documented setup evidence requires source and review date")
        return self


class HardConstraints(DomainModel):
    requires_offline: bool = False
    requires_free_plan: bool = False
    requires_open_source: bool = False
    allows_online_preparation: bool = False


class StarterStep(DomainModel):
    instruction: LocalizedText
    source_url: HttpUrl


class StarterGuide(DomainModel):
    prerequisites: list[LocalizedText]
    steps: list[StarterStep] = Field(min_length=3, max_length=5)
    example: LocalizedText
    expected_outcome: LocalizedText
    reviewed_at: date


class OperationSetup(DomainModel):
    id: SetupIdentifier
    name: LocalizedText
    task: LocalizedText
    stage: Literal["analysis", "design", "implementation", "testing"]
    domain: Literal["software", "artificial_intelligence", "cybersecurity"]
    platform: LocalizedText
    version: SetupIdentifier | None = None
    local_components: list[LocalizedText] = Field(min_length=1)
    model: LocalizedText | None = None
    preparation_network: NetworkRequirement
    runtime_network: NetworkRequirement
    offline_features: list[LocalizedText] = Field(default_factory=list)
    online_only_features: list[LocalizedText] = Field(default_factory=list)
    hardware_requirements: LocalizedText | None = None
    download_requirements: LocalizedText | None = None
    offline: CapabilityEvidence
    free_plan: CapabilityEvidence
    open_source: CapabilityEvidence
    evidence_status: EvidenceStatus
    evidence: list[SetupEvidence] = Field(min_length=1)
    starter_guide: StarterGuide

    @model_validator(mode="after")
    def prevent_broader_offline_claims(self) -> Self:
        if (
            self.offline.value is True
            and self.runtime_network is not NetworkRequirement.NOT_REQUIRED
        ):
            raise ValueError("offline claim conflicts with runtime network requirement")
        if self.offline.value is True and self.evidence_status in {
            EvidenceStatus.UNDOCUMENTED,
            EvidenceStatus.CONFLICTING,
        }:
            raise ValueError("offline claim requires resolved documented evidence")
        return self


class ToolProfile(DomainModel):
    offline: CapabilityEvidence
    free_plan: CapabilityEvidence
    open_source: CapabilityEvidence
    deployment: LocalizedText
    pricing_summary: LocalizedText
    learning_curve: LocalizedText
    integrations: list[LocalizedText]
    sources: list[HttpUrl] = Field(min_length=1)
    reviewed_at: date
    starter_guide: StarterGuide
    operation_setups: list[OperationSetup] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_and_date_consistency(self) -> Self:
        sources = set(self.sources)
        if len(sources) != len(self.sources):
            raise ValueError("profile sources must be unique")
        for capability in (self.offline, self.free_plan, self.open_source):
            if capability.source_url is not None and capability.source_url not in sources:
                raise ValueError("capability source must be listed in profile sources")
            if capability.reviewed_at and capability.reviewed_at > self.reviewed_at:
                raise ValueError("capability review cannot be later than profile review")
        if self.starter_guide.reviewed_at > self.reviewed_at:
            raise ValueError("guide review cannot be later than profile review")
        if any(step.source_url not in sources for step in self.starter_guide.steps):
            raise ValueError("starter step source must be listed in profile sources")
        setup_ids = [setup.id for setup in self.operation_setups]
        if len(setup_ids) != len(set(setup_ids)):
            raise ValueError("operation setup ids must be unique")
        for setup in self.operation_setups:
            referenced = {
                evidence.source_url
                for evidence in setup.evidence
                if evidence.source_url is not None
            }
            referenced.update(
                capability.source_url
                for capability in (setup.offline, setup.free_plan, setup.open_source)
                if capability.source_url is not None
            )
            referenced.update(step.source_url for step in setup.starter_guide.steps)
            if not referenced <= sources:
                raise ValueError("operation setup sources must be listed in profile sources")
        return self
