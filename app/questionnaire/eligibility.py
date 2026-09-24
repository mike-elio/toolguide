"""Hard requirements never become scoring preferences."""

from pydantic import Field

from app.domain.models import DomainModel, Identifier, LocalizedText, Tool
from app.domain.tool_profiles import HardConstraints, NetworkRequirement, OperationSetup


CAPABILITY_FIELDS = {
    "requires_offline": "offline",
    "requires_free_plan": "free_plan",
    "requires_open_source": "open_source",
}


class EligibilityDecision(DomainModel):
    tool_id: Identifier
    tool_name: LocalizedText
    eligible: bool
    failed_constraints: list[str] = Field(default_factory=list)
    unknown_constraints: list[str] = Field(default_factory=list)
    matching_setup_id: str | None = None


class NoMatchAlternative(DomainModel):
    tool_id: Identifier
    tool_name: LocalizedText
    setup_id: str
    setup_name: LocalizedText
    changed_constraints: list[str] = Field(min_length=1)


def _matching_setups(tool: Tool) -> list[OperationSetup]:
    if tool.profile is None:
        return []
    return [
        setup for setup in tool.profile.operation_setups
        if setup.stage in tool.stages and setup.domain == tool.domain
    ]


def _evaluate_setup(
    setup: OperationSetup, constraints: HardConstraints
) -> tuple[list[str], list[str]]:
    failed, unknown = [], []
    for requirement, capability in CAPABILITY_FIELDS.items():
        if not getattr(constraints, requirement):
            continue
        evidence = getattr(setup, capability)
        if evidence.value is None:
            unknown.append(requirement)
        elif evidence.value is False:
            failed.append(requirement)
    if constraints.requires_offline:
        if setup.runtime_network is NetworkRequirement.UNKNOWN:
            unknown.append("requires_offline")
        elif setup.runtime_network is not NetworkRequirement.NOT_REQUIRED:
            failed.append("requires_offline")
        if (
            setup.preparation_network is NetworkRequirement.REQUIRED
            and not constraints.allows_online_preparation
        ):
            failed.append("allows_online_preparation")
        elif setup.preparation_network is NetworkRequirement.UNKNOWN:
            unknown.append("allows_online_preparation")
    return list(dict.fromkeys(failed)), list(dict.fromkeys(unknown))


def evaluate_eligibility(tool: Tool, constraints: HardConstraints) -> EligibilityDecision:
    if tool.profile and tool.profile.operation_setups:
        setup_results = [
            (setup, *_evaluate_setup(setup, constraints))
            for setup in _matching_setups(tool)
        ]
        if not setup_results:
            return EligibilityDecision(
                tool_id=tool.id, tool_name=tool.name, eligible=False,
                unknown_constraints=["task_scope"],
            )
        for setup, failed, unknown in setup_results:
            if not failed and not unknown:
                return EligibilityDecision(
                    tool_id=tool.id,
                    tool_name=tool.name,
                    eligible=True,
                    matching_setup_id=setup.id,
                )
        failed = sorted({item for _, failures, _ in setup_results for item in failures})
        unknown = sorted({item for _, _, unknowns in setup_results for item in unknowns})
        return EligibilityDecision(
            tool_id=tool.id,
            tool_name=tool.name,
            eligible=False,
            failed_constraints=failed,
            unknown_constraints=unknown,
        )

    failed, unknown = [], []
    for requirement, capability in CAPABILITY_FIELDS.items():
        if not getattr(constraints, requirement):
            continue
        evidence = getattr(tool.profile, capability) if tool.profile else None
        if evidence is None or evidence.value is None:
            unknown.append(requirement)
        elif evidence.value is False:
            failed.append(requirement)
    return EligibilityDecision(tool_id=tool.id, tool_name=tool.name, eligible=not (failed or unknown),
                               failed_constraints=failed, unknown_constraints=unknown)


def find_minimal_alternatives(
    tools: list[Tool], constraints: HardConstraints, *, limit: int = 3
) -> list[NoMatchAlternative]:
    """Return documented setups requiring the fewest explicit constraint changes."""
    candidates: list[NoMatchAlternative] = []
    for tool in tools:
        if tool.profile is None:
            continue
        documented_setups: list[NoMatchAlternative] = []
        for setup in _matching_setups(tool):
            failed, unknown = _evaluate_setup(setup, constraints)
            if not failed or unknown:
                continue
            documented_setups.append(
                NoMatchAlternative(
                    tool_id=tool.id,
                    tool_name=tool.name,
                    setup_id=setup.id,
                    setup_name=setup.name,
                    changed_constraints=sorted(failed),
                )
            )
        if documented_setups:
            candidates.append(
                min(
                    documented_setups,
                    key=lambda item: (
                        len(item.changed_constraints),
                        item.changed_constraints,
                        item.setup_id,
                    ),
                )
            )
    if not candidates:
        return []
    minimum_changes = min(len(item.changed_constraints) for item in candidates)
    return [
        item
        for item in candidates
        if len(item.changed_constraints) == minimum_changes
    ][:limit]
