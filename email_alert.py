"""
email_alert.py

Sends an automated email alert when the anomaly agent detects a flagged
metric. Uses Gmail's SMTP with an "app password" (free, no paid API needed).

Setup:
  1. Enable 2-Step Verification on your Google account
  2. Create an App Password: https://myaccount.google.com/apppasswords
  3. Set these as environment variables (never hardcode credentials):
       EMAIL_SENDER=you@gmail.com
       EMAIL_APP_PASSWORD=your_16_char_app_password
       EMAIL_RECEIVER=you@gmail.com   (can be the same address for testing)
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from anomaly_agent import build_report


def format_email_body(report: dict) -> str:
    if not report["anomalies"]:
        return f"No anomalies detected in the data through {report['report_date'].date()}. All metrics within normal range."

    lines = [
        f"Anomaly report for {report['report_date'].strftime('%B %d, %Y')}",
        f"{len(report['anomalies'])} anomalies flagged in the last {report['lookback_days']} days.",
        "",
    ]
    for a in report["anomalies"]:
        lines.append(f"- [{a.severity.upper()}] {a.date.strftime('%b %d')}: {a.explanation}")

    for d, note in report["cross_reference_notes"].items():
        lines.append("")
        lines.append(f"Analyst note ({d.strftime('%b %d')}): {note}")

    lines.append("")
    lines.append("Full report attached (anomaly_report.pdf).")
    return "\n".join(lines)


def send_alert(report: dict, attachment_path: str = "anomaly_report.pdf"):
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_APP_PASSWORD")
    receiver = os.environ.get("EMAIL_RECEIVER", sender)

    if not sender or not password:
        raise EnvironmentError(
            "EMAIL_SENDER / EMAIL_APP_PASSWORD not set. See module docstring for setup."
        )

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = f"[Anomaly Agent] {report['status']} - {report['report_date'].strftime('%b %d, %Y')}"
    msg.attach(MIMEText(format_email_body(report), "plain"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            from email.mime.application import MIMEApplication
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

    print(f"Alert email sent to {receiver}")


if __name__ == "__main__":
    report = build_report("business_metrics.xlsx")
    if report["anomalies"]:
        send_alert(report)
    else:
        print("No anomalies - no alert sent.")
