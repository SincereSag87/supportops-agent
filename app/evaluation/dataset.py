from pathlib import Path

from app.evaluation.models import SupportAgentBenchmark


def load_benchmark(path: str | Path) -> SupportAgentBenchmark:
    return SupportAgentBenchmark.from_file(path)
