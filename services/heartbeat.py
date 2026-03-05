from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)


class PixelOfficeHeartbeat:
    STARTUP_TASK = "Starting CryptoEye Agent services"
    ONLINE_TASK = "Serving Telegram updates and monitor jobs"

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        agent_id: str,
        name: str,
        role: str,
        role_label_zh: str,
        enabled: bool = True,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.role_label_zh = role_label_zh
        self.enabled = enabled and bool(endpoint) and bool(api_key) and bool(agent_id)
        self._client: httpx.AsyncClient | None = None
        self._last_state: tuple[str, str] | None = None
        self._last_exception_signature: str = ""
        self._last_exception_at: float = 0.0

    @classmethod
    def from_config(cls, config_module) -> "PixelOfficeHeartbeat":
        return cls(
            endpoint=config_module.PIXEL_OFFICE_ENDPOINT,
            api_key=config_module.PIXEL_OFFICE_API_KEY,
            agent_id=config_module.PIXEL_OFFICE_AGENT_ID,
            name=config_module.PIXEL_OFFICE_AGENT_NAME,
            role=config_module.PIXEL_OFFICE_AGENT_ROLE,
            role_label_zh=config_module.PIXEL_OFFICE_AGENT_ROLE_LABEL_ZH,
            enabled=config_module.PIXEL_OFFICE_HEARTBEAT_ENABLED,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=10.0,
                headers={
                    "apikey": self.api_key,
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                },
            )
        return self._client

    async def report(self, status: str, current_task: str = "", force: bool = False) -> None:
        if not self.enabled:
            return

        current_task = (current_task or "").strip()
        state = (status, current_task)
        if not force and self._last_state == state:
            return

        payload = {
            "id": self.agent_id,
            "status": status,
            "current_task": current_task,
            "name": self.name,
            "role": self.role,
            "role_label_zh": self.role_label_zh,
        }
        try:
            client = await self._get_client()
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            self._last_state = state
        except Exception as exc:
            logger.warning("Heartbeat report failed: %s", exc)

    async def report_starting(self) -> None:
        await self.report("working", self.STARTUP_TASK)

    async def report_online(self) -> None:
        await self.report("working", self.ONLINE_TASK)

    async def report_stopped(self) -> None:
        await self.report("sleeping", "")

    async def report_exception(self, error: Exception, prefix: str = "Runtime exception") -> None:
        if not self.enabled:
            return

        message = " ".join(str(error).split())
        task = f"{prefix}: {error.__class__.__name__}"
        if message:
            task = f"{task} - {message}"
        task = task[:220]

        signature = task
        now = time.monotonic()
        if signature == self._last_exception_signature and now - self._last_exception_at < 60:
            return

        self._last_exception_signature = signature
        self._last_exception_at = now
        await self.report("thinking", task, force=True)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
