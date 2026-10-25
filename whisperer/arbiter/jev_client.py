"""Jev / System One Client Wrapper for high-speed decision evaluations."""

import logging
import time
from typing import Any, Dict, Optional
from typesafe_sdk import (
    AsyncTypeSafeClient,
    Choice,
    Noul,
    RetryPolicy,
    Score,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAuthenticationError,
)

from whisperer.config import settings

logger = logging.getLogger("whisperer.arbiter")


class JevClientWrapper:
    """Production-grade wrapper around TypeSafe SDK supporting async speculative fan-out."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or settings.get_arbiter_api_key()
        self.base_url = base_url or settings.JEV_BASE_URL
        self.model = model or settings.JEV_MODEL
        self.timeout = timeout or settings.REQUEST_TIMEOUT_SECONDS

        if not self.api_key:
            logger.warning(
                "No API key provided for System One Arbiter. Set LAYA_IMPOSSIBLE_API_KEY in .env"
            )

        self.retry_policy = RetryPolicy(
            max_retries=settings.MAX_RETRIES,
            backoff_initial=0.5,
            backoff_max=4.0,
            backoff_jitter=0.20,
            http_statuses={408, 429, 500, 502, 503, 504, 529},
            respect_retry_after=True,
        )

    async def evaluate_async(
        self,
        state: Any,
        questions: Dict[str, Any],
        model_override: Optional[str] = None,
    ) -> tuple[SystemOneResponse, float]:
        """Execute a speculative fan-out evaluation asynchronously within the active event loop.
        
        Returns:
            Tuple of (SystemOneResponse, latency_in_ms)
        """
        start = time.perf_counter()
        target_model = model_override or self.model

        async with AsyncTypeSafeClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=target_model,
            retry=self.retry_policy,
            timeout=self.timeout,
        ) as client:
            try:
                response = await client.system_one(state=state, questions=questions)
                latency_ms = (time.perf_counter() - start) * 1000.0
                logger.info(
                    "Jev evaluated %d questions in %.1f ms [model=%s]",
                    len(questions),
                    latency_ms,
                    response.model,
                )
                return response, latency_ms

            except TypeSafeAuthenticationError as auth_err:
                logger.error("Jev Authentication Failure: %s", auth_err)
                raise
            except TypeSafeAPIConnectionError as conn_err:
                logger.error("Jev Network Transport Failure: %s", conn_err)
                raise
            except TypeSafeAPIError as api_err:
                logger.error(
                    "Jev Server Error %s [Req: %s]: %s",
                    getattr(api_err, "status", "unknown"),
                    getattr(api_err, "request_id", "none"),
                    api_err,
                )
                raise


_client_instance: Optional[JevClientWrapper] = None


def get_jev_client() -> JevClientWrapper:
    """Singleton provider for JevClientWrapper."""
    global _client_instance
    if _client_instance is None:
        _client_instance = JevClientWrapper()
    return _client_instance
