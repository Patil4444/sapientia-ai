"""
Alert dispatcher — sends email alerts for critical/medium incidents.
Uses SendGrid for email. Falls back to console log if no API key.
"""
import os
import json
from datetime import datetime


def send_alert(incident: dict, analysis: dict, recipient_email: str = None,
               sendgrid_key: str = None) -> dict:
    """
    Send an alert for a new incident. Returns a result dict with status.
    """
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        r = httpx.post(
            f"{base}/api/alerts/send",
            json={
                "incident": incident,
                "analysis": analysis,
                "recipient_email": recipient_email,
                "sendgrid_key": sendgrid_key,
            },
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()

    severity  = analysis.get("severity", "LOW")
    itype     = analysis.get("incident_type", "Unknown")
    recordable = analysis.get("osha_recordable", False)
    project   = incident.get("project", "Unknown Project")
    reporter  = incident.get("reported_by", "Unknown")
    timestamp = incident.get("timestamp", datetime.now().isoformat())

    subject = f"[{severity}] Construction Safety Incident — {itype} @ {project}"

    body_html = f"""
    <div style="font-family: monospace; max-width: 600px; margin: 0 auto;">
      <div style="background: #0f0f0f; color: #FF6B00; padding: 16px 20px; font-size: 18px; font-weight: bold;">
        🦺 Sapientia — Incident Alert
      </div>
      <div style="background: {"#FF1744" if severity=="CRITICAL" else "#FF6B00" if severity=="MEDIUM" else "#2E7D32"};
                  color: white; padding: 10px 20px; font-size: 14px; font-weight: bold;">
        SEVERITY: {severity}  |  {itype}  |  {"⚠ OSHA RECORDABLE" if recordable else "Not Recordable"}
      </div>
      <div style="background: #f5f2ed; padding: 20px; border-left: 4px solid #FF6B00;">
        <table style="width:100%; font-size:13px; border-collapse:collapse;">
          <tr><td style="padding:6px 0; color:#888; width:140px;">Project</td>
              <td style="padding:6px 0; font-weight:bold;">{project}</td></tr>
          <tr><td style="padding:6px 0; color:#888;">Reported By</td>
              <td style="padding:6px 0;">{reporter}</td></tr>
          <tr><td style="padding:6px 0; color:#888;">Date/Time</td>
              <td style="padding:6px 0;">{timestamp}</td></tr>
          <tr><td style="padding:6px 0; color:#888;">Location</td>
              <td style="padding:6px 0;">{analysis.get("location_on_site","—")}</td></tr>
          <tr><td style="padding:6px 0; color:#888;">Injured Person</td>
              <td style="padding:6px 0;">{analysis.get("injured_person","Unknown")}</td></tr>
        </table>
        <hr style="border:none; border-top:1px solid #e0d9d0; margin:16px 0;"/>
        <b style="font-size:12px; color:#888;">INCIDENT SUMMARY</b><br/>
        <p style="font-size:13px; margin:8px 0;">{analysis.get("summary","—")}</p>
        <hr style="border:none; border-top:1px solid #e0d9d0; margin:16px 0;"/>
        <b style="font-size:12px; color:#888;">IMMEDIATE ACTIONS REQUIRED</b>
        <ol style="font-size:13px; margin:8px 0; padding-left:20px;">
          {"".join(f"<li style='margin-bottom:6px;'>{a}</li>" for a in analysis.get("immediate_actions_required",[]))}
        </ol>
      </div>
      <div style="background:#0f0f0f; color:#666; padding:10px 20px; font-size:11px;">
        Sapientia · Automated Safety Reporting · This alert was auto-generated
      </div>
    </div>
    """

    result = {
        "attempted":  True,
        "timestamp":  datetime.now().isoformat(),
        "recipient":  recipient_email,
        "subject":    subject,
        "severity":   severity,
    }

    # Try SendGrid if key provided
    if sendgrid_key and recipient_email:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail
            sg = sendgrid.SendGridAPIClient(api_key=sendgrid_key)
            message = Mail(
                from_email="alerts@sapientia",
                to_emails=recipient_email,
                subject=subject,
                html_content=body_html
            )
            response = sg.send(message)
            result["success"] = response.status_code in (200, 202)
            result["status_code"] = response.status_code
            result["method"] = "sendgrid"
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["method"] = "sendgrid_failed"
    else:
        # Simulate — log to console and return success for demo
        print(f"\n{'='*60}")
        print(f"[ALERT SIMULATED — no SendGrid key configured]")
        print(f"TO:      {recipient_email or 'safety.manager@example.com'}")
        print(f"SUBJECT: {subject}")
        print(f"SEVERITY: {severity} | OSHA: {recordable}")
        print(f"{'='*60}\n")
        result["success"] = True
        result["method"]  = "simulated"

    return result


def should_alert(severity: str) -> bool:
    """Only alert on CRITICAL and MEDIUM — don't spam for LOW."""
    return severity in ("CRITICAL", "MEDIUM")
