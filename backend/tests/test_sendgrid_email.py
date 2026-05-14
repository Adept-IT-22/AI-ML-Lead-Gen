import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from outreach_module.sendgrid.email_sending import SendGridSender

@pytest.mark.asyncio
async def test_sendgrid_create_client():
    sender = SendGridSender()
    with patch('outreach_module.sendgrid.email_sending.SendGridAPIClient') as mock_client:
        client = await sender.create_client(api_key="test_key")
        mock_client.assert_called_once_with("test_key")
        assert client == mock_client.return_value

@pytest.mark.asyncio
async def test_sendgrid_create_mail():
    from sendgrid.helpers.mail import Mail
    sender = SendGridSender()
    with patch('outreach_module.sendgrid.email_sending.get_unsubscribe_footer', return_value=" unsub_footer"):
        email = await sender.create_mail(
            email_to="test@example.com",
            subject="Test Subject",
            content="Test Content",
            unsubscribe_token="token123"
        )
        
        assert isinstance(email, Mail)
        assert email.from_email.email == "antony@adeptech.co.ke"
        assert email.subject.subject == "Test Subject"

@pytest.mark.asyncio
async def test_sendgrid_send_email():
    sender = SendGridSender()
    
    mock_response = MagicMock()
    mock_response.status_code = 202
    
    mock_client = MagicMock()
    mock_client.send.return_value = mock_response
    
    with patch.object(SendGridSender, 'create_client', return_value=mock_client), \
         patch.object(SendGridSender, 'create_mail', return_value=MagicMock()) as mock_create_mail, \
         patch('outreach_module.sendgrid.email_sending.ReplyTo') as mock_reply_to, \
         patch('outreach_module.sendgrid.email_sending.From') as mock_from, \
         patch('outreach_module.sendgrid.email_sending.TrackingSettings') as mock_tracking:
        
        response = await sender.send_email(
            to="test@example.com",
            subject="Test Subject",
            content="Test Content",
            unsubscribe_token="token123"
        )
        
        assert response.status_code == 202
        mock_client.send.assert_called_once()
