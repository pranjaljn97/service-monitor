from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.models.status import Component, OverallStatus

router = APIRouter(tags=["status"])


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    provider = request.app.state.provider
    overall, components = await provider.fetch_summary()
    incidents = await provider.fetch_incidents()

    non_operational = [c for c in components if c.status.value != "operational"]
    unresolved = [i for i in incidents if i.status.value != "resolved"]
    recent_resolved = [i for i in incidents if i.status.value == "resolved"][:5]

    if overall.indicator == "none":
        status_color = "#22c55e"
        status_bg = "#f0fdf4"
    elif overall.indicator == "minor":
        status_color = "#eab308"
        status_bg = "#fefce8"
    elif overall.indicator == "major":
        status_color = "#f97316"
        status_bg = "#fff7ed"
    else:
        status_color = "#ef4444"
        status_bg = "#fef2f2"

    # Build components HTML
    components_html = ""
    for c in components:
        if c.status.value == "operational":
            dot = '<span style="color:#22c55e">&#9679;</span>'
            label = "Operational"
        elif c.status.value == "degraded_performance":
            dot = '<span style="color:#eab308">&#9679;</span>'
            label = "Degraded"
        elif c.status.value == "partial_outage":
            dot = '<span style="color:#f97316">&#9679;</span>'
            label = "Partial Outage"
        else:
            dot = '<span style="color:#ef4444">&#9679;</span>'
            label = c.status.value.replace("_", " ").title()
        components_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:8px 0;border-bottom:1px solid #e5e7eb">'
            f'<span>{c.name}</span>'
            f'<span>{dot} {label}</span></div>'
        )

    # Build incidents HTML
    incidents_html = ""
    for inc in (unresolved + recent_resolved):
        impact_colors = {
            "critical": "#ef4444", "major": "#f97316",
            "minor": "#eab308", "none": "#6b7280",
        }
        color = impact_colors.get(inc.impact.value, "#6b7280")
        badge = (
            f'<span style="background:{color};color:white;padding:2px 8px;'
            f'border-radius:4px;font-size:12px">{inc.impact.value}</span>'
        )
        status_badge = (
            f'<span style="background:#e5e7eb;padding:2px 8px;'
            f'border-radius:4px;font-size:12px">{inc.status.value}</span>'
        )
        ts = inc.updated_at.strftime("%Y-%m-%d %H:%M UTC")
        latest_body = ""
        if inc.incident_updates:
            body = inc.incident_updates[0].body
            if body:
                latest_body = f'<p style="color:#6b7280;margin:4px 0 0 0;font-size:14px">{body}</p>'
        incidents_html += (
            f'<div style="padding:12px 0;border-bottom:1px solid #e5e7eb">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<strong>{inc.name}</strong>'
            f'<span>{badge} {status_badge}</span></div>'
            f'<p style="color:#9ca3af;margin:4px 0 0 0;font-size:12px">{ts}</p>'
            f'{latest_body}</div>'
        )

    if not incidents_html:
        incidents_html = '<p style="color:#6b7280;padding:12px 0">No recent incidents.</p>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Service Monitor - {provider.name.upper()}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 720px; margin: 0 auto; padding: 20px; background: #f9fafb; color: #111827; }}
        h1 {{ font-size: 24px; margin-bottom: 4px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; margin: 16px 0;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .status-banner {{ background: {status_bg}; border: 1px solid {status_color};
                          border-radius: 8px; padding: 16px 20px; margin: 16px 0;
                          display: flex; align-items: center; gap: 12px; }}
        .status-dot {{ width: 12px; height: 12px; border-radius: 50%;
                       background: {status_color}; display: inline-block; }}
        .api-links {{ display: flex; gap: 12px; margin: 16px 0; flex-wrap: wrap; }}
        .api-links a {{ color: #2563eb; font-size: 13px; text-decoration: none; }}
        .api-links a:hover {{ text-decoration: underline; }}
        h2 {{ font-size: 18px; margin: 0 0 12px 0; }}
        .footer {{ text-align: center; color: #9ca3af; font-size: 13px; margin-top: 32px; }}
    </style>
    <meta http-equiv="refresh" content="60">
</head>
<body>
    <h1>Service Monitor</h1>
    <p style="color:#6b7280;margin-top:0">Tracking {provider.name.upper()} Status Page</p>

    <div class="status-banner">
        <span class="status-dot"></span>
        <strong>{overall.description}</strong>
        <span style="color:#6b7280;margin-left:auto;font-size:14px">{len(components)} components</span>
    </div>

    <div class="api-links">
        API: <a href="/status">/status</a>
        <a href="/components">/components</a>
        <a href="/incidents">/incidents</a>
        <a href="/events/stream">/events/stream (SSE)</a>
    </div>

    <div class="card">
        <h2>Components</h2>
        {components_html}
    </div>

    <div class="card">
        <h2>Recent Incidents</h2>
        {incidents_html}
    </div>

    <div class="footer">Auto-refreshes every 60s | Polling {provider.name.upper()} every {request.app.state.settings.openai_poll_interval}s</div>
</body>
</html>"""
    return html


@router.get("/status")
async def get_status(request: Request) -> dict:
    provider = request.app.state.provider
    overall, components = await provider.fetch_summary()
    return {
        "provider": provider.name,
        "status": overall.model_dump(),
        "component_count": len(components),
    }


@router.get("/components")
async def get_components(request: Request) -> list[Component]:
    provider = request.app.state.provider
    _, components = await provider.fetch_summary()
    return components
