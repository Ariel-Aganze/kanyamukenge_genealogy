"""
Mailjet Email Backend for Django
Sends emails using Mailjet's HTTP API instead of SMTP
Perfect for hosting platforms like Render that block SMTP traffic
"""

import requests
import json
import logging
import base64
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage
from django.conf import settings
from decouple import config

# Set up logger
logger = logging.getLogger('mailjet')


class MailjetEmailBackend(BaseEmailBackend):
    """
    Custom email backend that uses Mailjet's REST API
    instead of SMTP to send emails
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently)
        
        # Get Mailjet credentials from environment
        self.api_key = config('MAILJET_API_KEY', default=None)
        self.secret_key = config('MAILJET_SECRET_KEY', default=None)
        
        # Mailjet API endpoints
        self.api_url = "https://api.mailjet.com/v3.1/send"
        
        # Validate configuration
        if not self.api_key or not self.secret_key:
            logger.error("❌ Mailjet API credentials not configured properly")
            if not self.fail_silently:
                raise ValueError("Mailjet API credentials (MAILJET_API_KEY, MAILJET_SECRET_KEY) must be configured")
        
        logger.info("✅ Mailjet email backend initialized successfully")

    def send_messages(self, email_messages):
        """
        Send multiple email messages
        Returns the number of successfully sent emails
        """
        if not email_messages:
            return 0
            
        sent_count = 0
        for message in email_messages:
            try:
                if self._send_single_message(message):
                    sent_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to send email: {str(e)}")
                if not self.fail_silently:
                    raise
        
        logger.info(f"📊 Mailjet batch send complete: {sent_count}/{len(email_messages)} emails sent successfully")
        return sent_count

    def _send_single_message(self, message):
        """
        Send a single email message via Mailjet API
        Returns True if successful, False otherwise
        """
        try:
            # Build email payload for Mailjet
            payload = self._build_mailjet_payload(message)
            
            # Send via Mailjet API
            response = self._make_api_request(payload)
            
            # Check response
            if response and response.status_code == 200:
                response_data = response.json()
                
                # Log success details
                if 'Messages' in response_data and response_data['Messages']:
                    message_info = response_data['Messages'][0]
                    status = message_info.get('Status', 'unknown')
                    message_id = message_info.get('To', [{}])[0].get('MessageID', 'unknown')
                    
                    logger.info(f"✅ Email sent successfully via Mailjet")
                    logger.info(f"   → To: {', '.join(message.to)}")
                    logger.info(f"   → Subject: {message.subject}")
                    logger.info(f"   → Status: {status}")
                    logger.info(f"   → Message ID: {message_id}")
                else:
                    logger.info(f"✅ Email sent via Mailjet to {', '.join(message.to)}")
                
                return True
            else:
                # Log error details
                error_msg = f"API request failed with status {response.status_code if response else 'No response'}"
                if response:
                    try:
                        error_details = response.json()
                        error_msg += f": {error_details}"
                    except:
                        error_msg += f": {response.text}"
                
                logger.error(f"❌ Mailjet API error: {error_msg}")
                logger.error(f"   → Failed to send to: {', '.join(message.to)}")
                logger.error(f"   → Subject: {message.subject}")
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception sending email via Mailjet: {str(e)}")
            logger.error(f"   → Failed to send to: {', '.join(message.to)}")
            logger.error(f"   → Subject: {message.subject}")
            return False

    def _build_mailjet_payload(self, message):
        """
        Build the JSON payload for Mailjet API from Django EmailMessage
        """
        # Extract sender information
        from_email = message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        # Parse "Name <email@domain.com>" format
        if '<' in from_email and '>' in from_email:
            # Split "Display Name <email@domain.com>"
            name_part = from_email.split('<')[0].strip().strip('"').strip("'")
            email_part = from_email.split('<')[1].strip('>')
            from_name = name_part if name_part else "Famille KANYAMUKENGE"
            from_address = email_part
        else:
            from_name = "Famille KANYAMUKENGE"
            from_address = from_email

        # Build recipients list
        recipients = []
        for to_email in message.to:
            recipients.append({"Email": to_email})

        # Build the main message object
        message_data = {
            "From": {
                "Email": from_address,
                "Name": from_name
            },
            "To": recipients,
            "Subject": message.subject,
        }

        # Add message body (text and/or HTML)
        if hasattr(message, 'body') and message.body:
            message_data["TextPart"] = message.body

        # Add HTML content if available
        if hasattr(message, 'alternatives') and message.alternatives:
            for content, content_type in message.alternatives:
                if content_type == 'text/html':
                    message_data["HTMLPart"] = content
                    break

        # Add CC recipients if any
        if hasattr(message, 'cc') and message.cc:
            cc_recipients = []
            for cc_email in message.cc:
                cc_recipients.append({"Email": cc_email})
            message_data["Cc"] = cc_recipients

        # Add BCC recipients if any
        if hasattr(message, 'bcc') and message.bcc:
            bcc_recipients = []
            for bcc_email in message.bcc:
                bcc_recipients.append({"Email": bcc_email})
            message_data["Bcc"] = bcc_recipients

        # Build final payload
        payload = {
            "Messages": [message_data]
        }

        return payload

    def _make_api_request(self, payload):
        """
        Make the actual HTTP request to Mailjet API
        """
        try:
            # Prepare authentication
            auth_string = f"{self.api_key}:{self.secret_key}"
            auth_header = base64.b64encode(auth_string.encode()).decode()

            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {auth_header}',
                'User-Agent': 'KANYAMUKENGE-Genealogy-Platform/1.0'
            }

            # Log request (without sensitive data)
            logger.debug(f"🚀 Making Mailjet API request")
            logger.debug(f"   → URL: {self.api_url}")
            logger.debug(f"   → Recipients: {len(payload['Messages'][0]['To'])} recipient(s)")

            # Make the request
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30  # 30 second timeout
            )

            logger.debug(f"📡 Mailjet API response: {response.status_code}")
            
            return response

        except requests.exceptions.Timeout:
            logger.error("❌ Mailjet API request timed out after 30 seconds")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("❌ Failed to connect to Mailjet API")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Mailjet API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error making Mailjet API request: {str(e)}")
            return None

    def open(self):
        """
        Open the backend (required by Django interface)
        For HTTP-based backends, this is typically a no-op
        """
        pass

    def close(self):
        """
        Close the backend (required by Django interface)
        For HTTP-based backends, this is typically a no-op
        """
        pass


class MailjetDebugBackend(MailjetEmailBackend):
    """
    Debug version of Mailjet backend that logs email content
    without actually sending emails (useful for development)
    """
    
    def _send_single_message(self, message):
        """
        Override to log email content without sending
        """
        logger.info("🧪 DEBUG MODE: Email would be sent via Mailjet")
        logger.info(f"   → To: {', '.join(message.to)}")
        logger.info(f"   → Subject: {message.subject}")
        logger.info(f"   → Body preview: {message.body[:100]}...")
        
        return True  # Always return success for debugging


def test_mailjet_configuration():
    """
    Test function to verify Mailjet configuration
    Can be called from Django shell or management command
    """
    try:
        backend = MailjetEmailBackend()
        
        # Test basic configuration
        if not backend.api_key or not backend.secret_key:
            return {
                'success': False,
                'error': 'Mailjet credentials not configured',
                'details': 'Set MAILJET_API_KEY and MAILJET_SECRET_KEY environment variables'
            }
        
        # Test basic API connectivity (you could extend this to make a test API call)
        logger.info("✅ Mailjet backend configuration test passed")
        return {
            'success': True,
            'message': 'Mailjet backend configured correctly',
            'api_key_length': len(backend.api_key),
            'secret_key_length': len(backend.secret_key)
        }
        
    except Exception as e:
        logger.error(f"❌ Mailjet configuration test failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


# Convenience function for testing from Django shell
def send_test_email(to_email, subject="Test from KANYAMUKENGE", body="This is a test email."):
    """
    Send a test email using the Mailjet backend
    Usage: from accounts.mailjet_backend import send_test_email; send_test_email('test@example.com')
    """
    from django.core.mail import send_mail
    
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info(f"✅ Test email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Test email failed: {str(e)}")
        return False