"""Validated aggregate for an in-memory knowledge-base snapshot."""

from typing import Self

from pydantic import Field, model_validator

from app.domain.models import Benchmark, DomainModel, Question, Rule, Stage, Tool


class KnowledgeSnapshot(DomainModel):
    """A self-contained, referentially valid knowledge-base view."""

    stages: list[Stage] = Field(default_factory=list)
    tools: list[Tool] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)
    benchmarks: list[Benchmark] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ids_and_references(self) -> Self:
        collections = {
            "stage": self.stages,
            "tool": self.tools,
            "question": self.questions,
            "rule": self.rules,
            "benchmark": self.benchmarks,
        }
        for label, items in collections.items():
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} ids must be unique")

        stage_ids = {stage.id for stage in self.stages}
        tools_by_id = {tool.id: tool for tool in self.tools}
        tool_ids = set(tools_by_id)
        questions_by_id = {question.id: question for question in self.questions}

        for tool in self.tools:
            for stage in tool.stages:
                if stage not in stage_ids:
                    raise ValueError(
                        f"tool references unknown stage: {tool.id} -> {stage}"
                    )

        for question in self.questions:
            if question.stage not in stage_ids:
                raise ValueError(
                    "question references unknown stage: "
                    f"{question.id} -> {question.stage}"
                )

        for rule in self.rules:
            question = questions_by_id.get(rule.question_id)
            if question is None:
                raise ValueError(
                    "rule references unknown question: "
                    f"{rule.id} -> {rule.question_id}"
                )
            answer_ids = {option.id for option in question.options} | {
                intent.id for intent in question.text_intents
            }
            if rule.answer_option_id not in answer_ids:
                raise ValueError(
                    "rule references unknown answer option or text intent: "
                    f"{rule.id} -> {rule.answer_option_id}"
                )
            for impact in rule.impacts:
                if impact.tool_id not in tool_ids:
                    raise ValueError(
                        "rule impact references unknown tool: "
                        f"{rule.id} -> {impact.tool_id}"
                    )
                tool = tools_by_id[impact.tool_id]
                if question.domain is not None and (
                    tool.domain is not question.domain
                    or question.stage not in tool.stages
                ):
                    raise ValueError(
                        "rule impact crosses a stage/domain pool: "
                        f"{rule.id} -> {impact.tool_id}"
                    )

        for benchmark in self.benchmarks:
            if benchmark.tool_id not in tool_ids:
                raise ValueError(
                    "benchmark references unknown tool: "
                    f"{benchmark.id} -> {benchmark.tool_id}"
                )
        return self
