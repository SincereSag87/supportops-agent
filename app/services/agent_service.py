from app.agent.models import AgentRequest
from app.agent.results import AgentResult
from app.agent.runner import AgentRunner


class AgentService:
    def __init__(self, runner: AgentRunner) -> None:
        self.runner = runner

    def handle_request(
        self,
        user_input: str,
        customer_id: str | None = None,
        model: str | None = None,
    ) -> AgentResult:
        request = AgentRequest(user_input=user_input, customer_id=customer_id)
        return self.runner.run(request, model=model)
