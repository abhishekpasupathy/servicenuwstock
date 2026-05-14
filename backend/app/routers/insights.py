from fastapi import APIRouter, Response

from app.services.data_fetcher import bars_to_frame, get_ohlcv, get_quote
from app.services.monte_carlo import run_monte_carlo
from app.services.narrative_engine import generate_insight
from app.services.quant_engine import compute_all_indicators
from app.services.risk_engine import compute_risk_metrics
from app.services.signal_engine import generate_signals

router = APIRouter(tags=["insights"])


async def _insight(ticker: str):
    bars = await get_ohlcv(ticker, "2y", "1d")
    df = bars_to_frame(bars)
    quote = await get_quote(ticker)
    quant = compute_all_indicators(df)
    sig = generate_signals(quant, quote["price"])
    risk = compute_risk_metrics(df, None, sig["buy_prob"] / 100)
    monte = run_monte_carlo(df, 2000, 90)
    return generate_insight(quant, sig, risk, monte, quote)


@router.get("/insights/{ticker}")
async def insights(ticker: str):
    return await _insight(ticker)


@router.get("/insights/{ticker}/pdf")
async def insights_pdf(ticker: str):
    insight = await _insight(ticker)
    html = f"<h1>{insight['verdict']}</h1><p>{insight['plain_english_summary']}</p><p>{insight['monte_carlo_narrative']}</p>"
    try:
        from weasyprint import HTML

        pdf = HTML(string=html).write_pdf()
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={ticker.upper()}-insight.pdf"},
        )
    except Exception:
        return Response(html, media_type="text/html")
