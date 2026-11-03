import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from emporio.agent.contract import Step


@dataclass(frozen=True)
class Outcome:
    answer: str
    steps: tuple[Step, ...]
    model: str | None
    fallback_used: bool


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _same(key: str, expected: str, actual: object) -> bool:
    actual = str(actual)
    if key == "phone":
        return _digits(expected) == _digits(actual)
    if key == "email":
        return expected.strip().casefold() == actual.strip().casefold()
    return re.sub(r"[\s#.-]", "", expected).upper() == re.sub(r"[\s#.-]", "", actual).upper()


def _tools(outcome: Outcome, name: str) -> list[Step]:
    return [step for step in outcome.steps if step.name == name and step.kind != "reasoning"]


@dataclass
class CalledTool(Evaluator):
    """Passes when the tool ran, and when given, when one call carried exactly these arguments."""

    tool: str
    arguments: Mapping[str, str] = field(default_factory=dict)

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool]:
        calls = _tools(ctx.output, self.tool)
        results = {f"called:{self.tool}": bool(calls)}
        if self.arguments:
            results[f"arguments:{self.tool}"] = any(
                all(_same(key, value, (call.inputs or {}).get(key, "")) for key, value in self.arguments.items())
                for call in calls
            )
        return results


@dataclass
class ReturnedSection(Evaluator):
    """Passes when a policy lookup brought back this manual section: tests the search, not the model."""

    section: str
    tool: str = "policy_lookup"

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool]:
        found = any(
            self.section == str(section.get("number"))
            for step in _tools(ctx.output, self.tool)
            if isinstance(step.result, dict)
            for section in step.result.get("sections", [])
        )
        return {f"section {self.section} found": found}


@dataclass
class Says(Evaluator):
    patterns: Sequence[str]

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool]:
        return {f"says:{p}": re.search(p, ctx.output.answer, re.IGNORECASE) is not None for p in self.patterns}


@dataclass
class NeverSays(Evaluator):
    patterns: Sequence[str]

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool]:
        return {f"never:{p}": re.search(p, ctx.output.answer, re.IGNORECASE) is None for p in self.patterns}
