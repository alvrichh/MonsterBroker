"""What the agent says to Claude when a strategy wants to trade."""

from __future__ import annotations

import json

from app.agent.state import Portfolio
from app.strategies.base import Signal

REVIEW_SYSTEM = """Eres el gestor de riesgo de MonsterBroker, un bot de trading cripto que opera en papel \
(dinero simulado, sin riesgo real). Una estrategia técnica propone una orden y tú la apruebas o la vetas.

Valora solo con lo que recibes: coherencia de los indicadores con la señal, tamaño de la orden frente al \
efectivo disponible, concentración en un único activo y si la señal llega tarde (RSI extremo, precio lejos de \
las bandas). No tienes noticias ni datos de otros mercados: no los inventes.

Responde únicamente con un objeto JSON, sin texto alrededor:
{"approve": true | false, "confidence": número entre 0 y 1, "rationale": "una o dos frases en español"}"""


def review_prompt(signal: Signal, indicators: dict[str, float | None], portfolio: Portfolio) -> str:
    context = {
        "signal": signal.model_dump(mode="json"),
        "indicators": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in indicators.items()},
        "portfolio": {
            "cash": round(portfolio.cash, 2),
            "positions": [p.model_dump() for p in portfolio.positions.values()],
            "recent_trades": [t.model_dump(mode="json") for t in portfolio.trades[-5:]],
        },
    }
    return json.dumps(context, ensure_ascii=False, indent=2)
