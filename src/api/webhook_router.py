"""Webhook Router — Receives external webhooks (e.g., CourtListener RECAP).

This module handles incoming webhooks, verifies them, and routes them to the
appropriate agents (like the Docket Monitor) for processing.
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

logger = logging.getLogger("cyphergy.api.webhook_router")

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.post("/courtlistener")
async def courtlistener_webhook(request: Request, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Receive and process CourtListener (RECAP) webhooks for docket updates."""
    # Verify webhook token if configured
    expected_token = os.getenv("COURTLISTENER_WEBHOOK_TOKEN")
    if expected_token:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header.split(" ")[1] != expected_token:
            logger.warning("Unauthorized CourtListener webhook attempt")
            raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Process in background to avoid blocking the webhook response
    background_tasks.add_task(_process_courtlistener_webhook, payload)
    
    return {"status": "accepted", "message": "Webhook received and queued for processing"}

async def _process_courtlistener_webhook(payload: Dict[str, Any]) -> None:
    """Background task to process the webhook payload."""
    try:
        from src.agents.docket_monitor import DocketMonitor
        
        # In a real app, we'd get the singleton instance from app state
        monitor = DocketMonitor()
        
        alert = await monitor.handle_courtlistener_webhook(payload)
        
        if alert:
            logger.info(f"Generated alert for case {alert.case_id}: {alert.plain_language_summary}")
            # Here we would trigger a notification to the user via the dashboard/email
            # e.g., await notification_service.send_alert(alert)
            
    except Exception as exc:
        logger.error(f"Error processing CourtListener webhook: {str(exc)}")
