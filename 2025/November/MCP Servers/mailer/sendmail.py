import smtplib
import json
from email.mime.text import MIMEText
from typing import List, Dict, Union

from mcp.server.fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP(
    name="SMTP_Mailer",
    instructions="A tool for sending email messages using smtp"
)

# --- Configurations ---
def load_config(file_path: str) -> Dict:
    """Loads a JSON configuration file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        return {}

SMTP_CONFIG = load_config('config.json')
MAILING_LIST = load_config('mailing_list.json')

def get_recipients(list_name: str = None, single_email: str = None) -> List[str]:
    """list of recipients"""
    if single_email:
        return [single_email]
    elif list_name and list_name in MAILING_LIST:
        return MAILING_LIST[list_name]
    return []

@mcp.tool()
def send_email(subject: str, body: str, list_name: str = None, single_email: str = None) -> Dict[str, Union[str, bool]]:
    
    if not SMTP_CONFIG:
        return {"success": False, "message": "SMTP configuration failed to load."}
        
    recipients = get_recipients(list_name, single_email)
    
    if not recipients:
        return {"success": False, "message": "No valid mailing list or single recipient specified."}
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_CONFIG['smtp_username']
    msg['To'] = ", ".join(recipients)
    
    try:
        # Port 465 requires SSL, use SMTP_SSL
        # Port 587 uses STARTTLS, use SMTP with starttls()
        smtp_port = SMTP_CONFIG.get('smtp_port', 465)
        
        if smtp_port == 465:
            # Use SSL for port 465
            with smtplib.SMTP_SSL(SMTP_CONFIG['smtp_server'], smtp_port) as server:
                server.login(SMTP_CONFIG['smtp_username'], SMTP_CONFIG['smtp_password'])
                server.sendmail(SMTP_CONFIG['smtp_username'], recipients, msg.as_string())
        else:
            # Use STARTTLS for port 587
            with smtplib.SMTP(SMTP_CONFIG['smtp_server'], smtp_port) as server:
                server.starttls()
                server.login(SMTP_CONFIG['smtp_username'], SMTP_CONFIG['smtp_password'])
                server.sendmail(SMTP_CONFIG['smtp_username'], recipients, msg.as_string())
        
        return {"success": True, "message": f"Email successfully sent to {len(recipients)} recipients."}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "SMTP Authentication Error"}
    except Exception as e:
        return {"success": False, "message": f"Failed to send email: {str(e)}"}