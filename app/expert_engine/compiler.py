import hashlib

from app.domain.models import Rule


TEMPLATES = """
(deftemplate tool
  (slot tool-id (type STRING)))

(deftemplate selected-answer
  (slot question-id (type STRING))
  (slot option-id (type STRING))
  (slot value (type FLOAT))
  (slot importance (type FLOAT)))

(deftemplate score-effect
  (slot tool-id (type STRING))
  (slot rule-id (type STRING))
  (slot value (type FLOAT)))

(deftemplate rule-fired
  (slot rule-id (type STRING)))
"""


def clips_rule_name(rule_id: str) -> str:
    digest = hashlib.sha256(rule_id.encode("utf-8")).hexdigest()
    return f"rule_{digest}"


def clips_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def compile_rule(rule: Rule) -> str:
    effects = "\n".join(
        "  (assert (score-effect "
        f"(tool-id {clips_string(impact.tool_id)}) "
        f"(rule-id {clips_string(rule.id)}) "
        f"(value (* ?value ?importance {impact.weight!r}))))"
        for impact in rule.impacts
    )
    return (
        f"(defrule {clips_rule_name(rule.id)}\n"
        "  (selected-answer "
        f"(question-id {clips_string(rule.question_id)}) "
        f"(option-id {clips_string(rule.answer_option_id)}) "
        "(value ?value) (importance ?importance))\n"
        "  =>\n"
        f"{effects}\n"
        f"  (assert (rule-fired (rule-id {clips_string(rule.id)}))))"
    )
