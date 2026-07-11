"""Mock AI provider — canned responses, no external calls. Built Day 1 on purpose."""


class MockProvider:
    """Deterministic stand-in for a real AIProvider, used until GeminiProvider lands on Day 3."""

    async def summarize(self, forecast_context: str) -> str:
        """Return a canned plain-language summary."""
        return "Sunny skies expected — output should track close to the seasonal average today."

    async def chat(self, message: str, forecast_context: str) -> str:
        """Return a canned chat reply, echoing the question for now."""
        return f"(mock) You asked: '{message}'. Real answers arrive once GeminiProvider is wired in."

    async def flag_anomaly(self, actual_kw: float, expected_kw: float, context: str) -> str | None:
        """Flag an anomaly using a simple threshold, worded in plain language."""
        if expected_kw <= 0:
            return None
        deviation_pct = abs(actual_kw - expected_kw) / expected_kw * 100
        if deviation_pct < 20:
            return None
        direction = "below" if actual_kw < expected_kw else "above"
        return f"(mock) Output is {deviation_pct:.0f}% {direction} the modeled estimate — worth a look."
