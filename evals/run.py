import contextlib
import io
import shutil
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path

from cases import Scenario, dataset
from evaluators import Outcome

from emporio.agent.store.agent import TOOLS, StoreAgent, store_now
from emporio.agent.store.prompt import STORE_ZONE
from emporio.agent.store.providers import build_model
from emporio.data.policy_index import read_settings
from emporio.data.store_db import DB_PATH

REPLY_LIMIT_SECONDS = 60
RUNS = 5
SOFT_THRESHOLD = 0.8
# A broken rule is never acceptable, while the rest may slip now and then because replies vary.
STRICT_PREFIXES = ("never:", "arguments:")


def task(scenario: Scenario) -> Outcome:
    settings = read_settings()
    model, primary = build_model(settings)
    with tempfile.TemporaryDirectory() as folder:
        scratch = Path(folder) / "emporio.sqlite"
        shutil.copy(DB_PATH, scratch)
        clock = store_now if scenario.today is None else (lambda: datetime.combine(scenario.today, time(10), STORE_ZONE))
        agent = StoreAgent(
            model,
            primary_model=primary,
            settings=settings,
            reply_timeout_seconds=REPLY_LIMIT_SECONDS,
            tools=TOOLS,
            db_path=scratch,
            clock=clock,
        )
        conversation_id = f"eval-{uuid.uuid4().hex}"
        steps, reply = [], None
        for message in scenario.messages:
            reply = agent.respond(conversation_id, message)
            steps += reply.details.steps
        return Outcome(reply.answer, tuple(steps), reply.details.model, reply.details.fallback_used)


def summarize(report) -> bool:
    passed: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for case in report.cases:
        for name, result in case.assertions.items():
            passed[case.source_case_name][name].append(bool(result.value))
    ok = True
    failed = total = 0
    for case, assertions in passed.items():
        print(f"\n{case}")
        for name, results in assertions.items():
            strict = name.startswith(STRICT_PREFIXES)
            rate = sum(results) / len(results)
            good = rate == 1 if strict else rate >= SOFT_THRESHOLD
            ok &= good
            failed += not good
            total += 1
            print(f"  {'PASS' if good else 'FAIL'}  {sum(results)}/{len(results)}  {name}{'  (zero tolerance)' if strict else ''}")
    for failure in report.failures:
        ok = False
        failed += 1
        print(f"\nFAILED RUN {failure.name}: {failure.error_message}")
    models = {case.output.model for case in report.cases}
    fallbacks = sum(case.output.fallback_used for case in report.cases)
    print(f"\nmodels: {sorted(m or '?' for m in models)}, replies from the fallback: {fallbacks}")
    print(f"\nRESULT: {'PASSED' if ok else 'FAILED'}, {failed} of {total} checks did not meet their bar (runs per case: {RUNS})")
    return ok


def main() -> None:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        report = dataset().evaluate_sync(task, repeat=RUNS, max_concurrency=2, progress=False)
    sys.exit(0 if summarize(report) else 1)


if __name__ == "__main__":
    main()
