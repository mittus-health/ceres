"""ChatModel adapter for Command Code (OpenAI-compatible chat completions).

Only transport lives here: no prompt, no parsing of the app's JSON.
"""

import ssl

import httpx
import truststore

# The model is a reasoning model: reasoning tokens count against this limit.
MAX_OUTPUT_TOKENS = 4000


class CommandCodeChatModel:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.id = f"commandcode:{model}"
        self._model = model
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(60.0, connect=10.0),
            # Trust the operating system's certificate store, so networks that
            # inspect HTTPS with their own CA work without disabling verification.
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        )

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.3,
                "max_tokens": MAX_OUTPUT_TOKENS,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    async def aclose(self) -> None:
        await self._client.aclose()
