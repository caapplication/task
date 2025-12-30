from __future__ import print_function
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from dotenv import load_dotenv
import os
import logging

# Set up logger
logger = logging.getLogger(__name__)

load_dotenv()

def send_task_creation_email(to_email: str, task_title: str, task_number: int, creator_name: str, task_description: str = None, due_date: str = None, priority: str = None):
    """Send email notification when a task is created"""
    logger.info(f"Attempting to send task creation email to {to_email} for task #{task_number}: {task_title}")
    
    try:
        API_KEY = os.getenv("SENDINBLUE_API_KEY") or os.getenv("API_KEY")
        SENDER = os.getenv("SENDER")
        REPLY_TO = os.getenv("REPLY_TO")
        NAME = os.getenv("NAME")
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8003")

        if not API_KEY:
            logger.warning("SENDINBLUE_API_KEY not found in environment variables - email sending disabled")
            return False
        
        if not SENDER:
            logger.warning("SENDER not found in environment variables - email sending may fail")
        
        logger.debug(f"Email configuration - Sender: {SENDER}, Reply-To: {REPLY_TO}, Name: {NAME}")

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        sender = {"name": NAME or "Task Management", "email": SENDER}
        reply_to = {"name": NAME or "Task Management", "email": REPLY_TO or SENDER}

        # Format due date if provided
        due_date_str = ""
        if due_date:
            due_date_str = f"<p style='color: #555; line-height: 1.6;'><strong>Due Date:</strong> {due_date}</p>"

        # Format priority if provided
        priority_str = ""
        if priority:
            priority_str = f"<p style='color: #555; line-height: 1.6;'><strong>Priority:</strong> {priority}</p>"

        # Format description if provided
        description_str = ""
        if task_description:
            description_str = f"<p style='color: #555; line-height: 1.6;'><strong>Description:</strong> {task_description}</p>"

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Task Assigned</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 20px auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <div style="text-align: center; padding-bottom: 20px; border-bottom: 1px solid #dddddd;">
            <h1 style="color: #333;">New Task Assigned</h1>
        </div>
        <div style="padding: 20px 0;">
            <p style="color: #555; line-height: 1.6;">Hello,</p>
            <p style="color: #555; line-height: 1.6;">A new task has been assigned to you by <strong>{creator_name}</strong>.</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="color: #333; line-height: 1.6; margin: 0;"><strong>Task #{task_number}: {task_title}</strong></p>
            </div>
            {description_str}
            {due_date_str}
            {priority_str}
            <p style="text-align: center; margin: 30px 0;">
                <a href="{FRONTEND_URL}/tasks" style="background-color: #007bff; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Task</a>
            </p>
        </div>
        <div style="text-align: center; padding-top: 20px; border-top: 1px solid #dddddd; font-size: 12px; color: #888;">
            <p>Best regards,<br>Task Management System</p>
        </div>
    </div>
</body>
</html>
"""

        subject = f"New Task Assigned: {task_title} (Task #{task_number})"
        logger.info(f"Preparing email notification - To: {to_email}, Subject: {subject}, Creator: {creator_name}, Task: #{task_number} '{task_title}'")
        logger.info(f"Email sender: {sender.get('name', 'N/A')} <{sender.get('email', 'N/A')}>")
        logger.info(f"Email reply-to: {reply_to.get('name', 'N/A')} <{reply_to.get('email', 'N/A')}>")
        logger.info(f"Email recipient: {to_email}")
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            reply_to=reply_to,
            html_content=html_content,
            sender=sender,
            subject=subject
        )

        logger.info(f"[EMAIL SENDING] Sending email via Sendinblue API")
        logger.info(f"[EMAIL SENDING] Recipient: {to_email}")
        logger.info(f"[EMAIL SENDING] Subject: {subject}")
        logger.info(f"[EMAIL SENDING] From: {sender.get('name', 'N/A')} <{sender.get('email', 'N/A')}>")
        logger.info(f"[EMAIL SENDING] Task Details - Number: #{task_number}, Title: {task_title}, Creator: {creator_name}")
        if due_date:
            logger.info(f"[EMAIL SENDING] Due Date: {due_date}")
        if priority:
            logger.info(f"[EMAIL SENDING] Priority: {priority}")
        
        api_response = api_instance.send_transac_email(send_smtp_email)
        message_id = getattr(api_response, 'message_id', 'N/A')
        
        logger.info(f"[EMAIL SENT SUCCESSFULLY] Email sent to: {to_email}")
        logger.info(f"[EMAIL SENT SUCCESSFULLY] Message ID: {message_id}")
        logger.info(f"[EMAIL SENT SUCCESSFULLY] Subject: {subject}")
        logger.info(f"[EMAIL SENT SUCCESSFULLY] Task: #{task_number} '{task_title}' assigned by {creator_name}")
        return True
        
    except ApiException as e:
        logger.error(f"Sendinblue API exception when sending email to {to_email}: {e}")
        logger.error(f"API Error details - Status: {e.status}, Reason: {e.reason}, Body: {e.body}")
        return False
    except Exception as e:
        logger.error(f"Error sending task creation email to {to_email}: {str(e)}", exc_info=True)
        return False

def send_task_comment_email(to_email: str, sender_name: str, task_title: str, task_number: int, comment_message: str = None, has_attachment: bool = False, attachment_name: str = None, task_url: str = None):
    """Send email notification when a comment is added to a task"""
    logger.info(f"Attempting to send task comment email to {to_email} for task #{task_number}: {task_title}")
    
    try:
        API_KEY = os.getenv("SENDINBLUE_API_KEY") or os.getenv("API_KEY")
        SENDER = os.getenv("SENDER")
        REPLY_TO = os.getenv("REPLY_TO")
        NAME = os.getenv("NAME")
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8003")
        
        if not API_KEY:
            logger.warning("SENDINBLUE_API_KEY not found in environment variables - email sending disabled")
            return False
        
        if not SENDER:
            logger.warning("SENDER not found in environment variables - email sending may fail")
        
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = API_KEY
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        
        sender = {"name": NAME or "Task Management", "email": SENDER}
        reply_to = {"name": NAME or "Task Management", "email": REPLY_TO or SENDER}
        
        # Format comment message
        comment_preview = ""
        if comment_message:
            preview_text = comment_message[:200] + "..." if len(comment_message) > 200 else comment_message
            comment_preview = f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff;">
                <p style="color: #333; line-height: 1.6; margin: 0; white-space: pre-wrap;">{preview_text}</p>
            </div>
            """
        
        # Format attachment info
        attachment_info = ""
        if has_attachment:
            attachment_name_display = attachment_name or "an attachment"
            attachment_info = f"""
            <p style="color: #555; line-height: 1.6; margin-top: 10px;">
                <strong>📎 Attachment:</strong> {attachment_name_display}
            </p>
            """
        
        task_view_url = task_url or f"{FRONTEND_URL}/tasks"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Comment on Task</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 20px auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <div style="text-align: center; padding-bottom: 20px; border-bottom: 1px solid #dddddd;">
            <h1 style="color: #333;">New Comment on Task</h1>
        </div>
        <div style="padding: 20px 0;">
            <p style="color: #555; line-height: 1.6;">Hello,</p>
            <p style="color: #555; line-height: 1.6;"><strong>{sender_name}</strong> commented on task <strong>#{task_number}: {task_title}</strong>.</p>
            {comment_preview}
            {attachment_info}
            <p style="text-align: center; margin: 30px 0;">
                <a href="{task_view_url}" style="background-color: #007bff; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Task & Reply</a>
            </p>
        </div>
        <div style="text-align: center; padding-top: 20px; border-top: 1px solid #dddddd; font-size: 12px; color: #888;">
            <p>Best regards,<br>Task Management System</p>
        </div>
    </div>
</body>
</html>
"""
        
        subject = f"New comment on Task #{task_number}: {task_title}"
        logger.info(f"Preparing email notification - To: {to_email}, Subject: {subject}, Sender: {sender_name}, Task: #{task_number} '{task_title}'")
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            reply_to=reply_to,
            html_content=html_content,
            sender=sender,
            subject=subject
        )
        
        logger.info(f"[EMAIL SENDING] Sending email via Sendinblue API")
        logger.info(f"[EMAIL SENDING] Recipient: {to_email}")
        logger.info(f"[EMAIL SENDING] Subject: {subject}")
        logger.info(f"[EMAIL SENDING] From: {sender.get('name', 'N/A')} <{sender.get('email', 'N/A')}>")
        logger.info(f"[EMAIL SENDING] Task: #{task_number} '{task_title}', Comment by: {sender_name}")
        
        api_response = api_instance.send_transac_email(send_smtp_email)
        message_id = getattr(api_response, 'message_id', 'N/A')
        
        logger.info(f"[EMAIL SENT SUCCESSFULLY] Email sent to: {to_email}")
        logger.info(f"[EMAIL SENT SUCCESSFULLY] Message ID: {message_id}")
        logger.info(f"[EMAIL SENT SUCCESSFULLY] Task: #{task_number} '{task_title}' - Comment by {sender_name}")
        return True
        
    except ApiException as e:
        logger.error(f"Sendinblue API exception when sending email to {to_email}: {e}")
        logger.error(f"API Error details - Status: {e.status}, Reason: {e.reason}, Body: {e.body}")
        return False
    except Exception as e:
        logger.error(f"Error sending task comment email to {to_email}: {str(e)}", exc_info=True)
        return False

