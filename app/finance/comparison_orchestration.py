from dataclasses import dataclass

@dataclass
class ForecastResult:
    method: str
    value: float
    low: float
    high: float
    confidence: str
    explanation: str
