import os
import requests


class AIClient:
    """
    Thin wrapper around the OpenAI provider call.
    Keeps provider logic isolated so it can be mocked in tests.
    """

    def __init__(self):
        # Support both env naming styles used across the project
        self.api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPEN_AI_API_KEY")
            or ""
        )

        self.model = (
            os.getenv("AI_MODEL")
            or os.getenv("OPEN_AI_MODEL")
            or "gpt-4o-mini"
        )

        self.base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
        self.timeout = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))

    def _extract_text_from_responses_api(self, data: dict) -> str:
        """
        Robustly extracts text from Responses API output.
        Handles both:
          - data["output_text"]
          - data["output"][...]["content"][...]["text"]
        """
        # Fast path (sometimes present)
        text = data.get("output_text")
        if isinstance(text, str) and text.strip():
            return text

        # Fallback: walk output array
        output = data.get("output", [])
        if not isinstance(output, list):
            output = []

        chunks: list[str] = []

        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue

            for c in content:
                if not isinstance(c, dict):
                    continue

                # Common shapes:
                # {"type":"output_text","text":"..."}
                # {"type":"text","text":"..."}
                t = c.get("text")
                if isinstance(t, str) and t.strip():
                    chunks.append(t)

        combined = "\n".join(chunks).strip()
        if combined:
            return combined

        # If we got here, we truly couldn't find text
        raise RuntimeError(f"Could not extract text from OpenAI response: keys={list(data.keys())}")

    def ask(self, prompt: str) -> str:
        """
        Sends a prompt to OpenAI and returns raw text output.
        Uses OpenAI Responses API.
        """
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set (check .env for OPEN_AI_API_KEY or OPENAI_API_KEY)"
            )

        url = f"{self.base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": prompt,
            "temperature": 0,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return self._extract_text_from_responses_api(data)