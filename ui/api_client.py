from typing import Any

import httpx

from ui.models import UIClientError


class SupportOpsAPIClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout: float = 15,
        agent_timeout: float = 120,
        evaluation_timeout: float = 900,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.agent_timeout = agent_timeout
        self.evaluation_timeout = evaluation_timeout
        self.transport = transport

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def ollama_health(self) -> dict[str, Any]:
        return self._request("GET", "/health/ollama")

    def state_health(self) -> dict[str, Any]:
        return self._request("GET", "/health/state")

    def list_customers(self) -> list[dict[str, Any]]:
        return self._request("GET", "/customers")

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        return self._request("GET", f"/customers/{customer_id}")

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/orders/{order_id}")

    def get_customer_orders(self, customer_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/customers/{customer_id}/orders")

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tickets/{ticket_id}")

    def get_customer_tickets(self, customer_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/customers/{customer_id}/tickets")

    def get_refund_policy(self) -> dict[str, Any]:
        return self._request("GET", "/policies/refund")

    def submit_agent_request(
        self,
        user_input: str,
        customer_id: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/agent/requests",
            json={"user_input": user_input, "customer_id": customer_id, "model": model},
            timeout=self.agent_timeout,
        )

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        return self._request("GET", "/approvals/pending")

    def get_approval(self, approval_id: str) -> dict[str, Any]:
        return self._request("GET", f"/approvals/{approval_id}")

    def approve(self, approval_id: str, actor: str, comment: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/approvals/{approval_id}/approve",
            json={"actor": actor, "comment": comment},
            timeout=self.agent_timeout,
        )

    def deny(self, approval_id: str, actor: str, comment: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/approvals/{approval_id}/deny",
            json={"actor": actor, "comment": comment},
        )

    def get_request_audit(self, request_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/audit/requests/{request_id}")

    def get_recent_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._request("GET", f"/audit/recent?limit={limit}")

    def list_benchmarks(self) -> list[dict[str, Any]]:
        return self._request("GET", "/evaluation/benchmarks")

    def run_evaluation(
        self,
        benchmark: str,
        mode: str = "scripted",
        model: str | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/evaluation/run",
            json={"benchmark": benchmark, "mode": mode, "model": model, "case_id": case_id},
            timeout=self.evaluation_timeout,
        )

    def run_demo_scenario(self, scenario_id: str) -> dict[str, Any]:
        return self._request("POST", f"/demo/scenarios/{scenario_id}", timeout=self.agent_timeout)

    def reset_demo(self, confirm: bool = True) -> dict[str, Any]:
        return self._request("POST", "/demo/reset", json={"confirm": confirm})

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        try:
            with httpx.Client(timeout=timeout or self.timeout, transport=self.transport) as client:
                response = client.request(method, f"{self.base_url}{path}", json=json)
        except httpx.ConnectError as exc:
            raise UIClientError(
                f"SupportOps API is unavailable at {self.base_url}.",
            ) from exc
        except httpx.TimeoutException as exc:
            raise UIClientError(
                "The API request timed out. Try again or use scripted demos."
            ) from exc
        except httpx.HTTPError as exc:
            raise UIClientError("The API request failed before a response was received.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise UIClientError("The API returned a malformed response.") from exc

        if response.status_code >= 400:
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            raise UIClientError(
                self._friendly_error(error.get("code"), error.get("message")),
                status_code=response.status_code,
            )
        return payload

    def _friendly_error(self, code: str | None, message: str | None) -> str:
        if code == "MODEL_NOT_AVAILABLE":
            return (
                "The selected local model is not installed. "
                "You can still use scripted demo scenarios and evaluation."
            )
        if code == "LLM_UNAVAILABLE":
            return "Ollama is unavailable. Scripted demos and benchmark mode still work."
        if code in {"APPROVALCONSUMEDERROR", "ApprovalConsumedError".upper()}:
            return "This approval has already been used and cannot authorize another action."
        if code and "APPROVAL" in code:
            return message or "The approval could not be applied."
        if code == "NOT_FOUND":
            return message or "The requested record was not found."
        if code == "RESET_CONFIRMATION_REQUIRED":
            return "Check the reset confirmation box before resetting synthetic demo state."
        return message or "The API returned an error."
