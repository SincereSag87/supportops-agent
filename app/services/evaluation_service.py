from pathlib import Path

from app.core.config import Settings
from app.evaluation.models import AgentEvaluationReport, EvaluationMode, SupportAgentBenchmark
from app.evaluation.runner import AgentEvaluationRunner


class EvaluationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.runner = AgentEvaluationRunner(settings=settings)

    def run(
        self,
        benchmark_path: str | Path,
        *,
        mode: EvaluationMode = EvaluationMode.SCRIPTED,
        model: str | None = None,
        case_id: str | None = None,
    ) -> AgentEvaluationReport:
        benchmark = SupportAgentBenchmark.from_file(benchmark_path)
        return self.runner.run_dataset(benchmark, mode=mode, model=model, case_id=case_id)
