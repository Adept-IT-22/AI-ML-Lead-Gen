import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from outreach_module.brevo.email_sending import BrevoSender

@pytest.mark.asyncio
async def test_brevo_create_client():
    sender = BrevoSender()
    with patch('outreach_module.brevo.email_sending.AsyncBrevo') as mock_brevo:
        client = await sender.create_client(api_key="test_key")
        mock_brevo.assert_called_once_with(api_key="test_key")
        assert client == mock_brevo.return_value

@pytest.mark.asyncio
async def test_brevo_send_email():
    sender = BrevoSender()
    
    # Mock response
    mock_response = MagicMock()
    mock_response.message_id = "test_message_id"
    
    # Mock client and its transactional_emails attribute
    mock_client = AsyncMock()
    # Transactional emails is an attribute of AsyncBrevo
    mock_transactional_emails = AsyncMock()
    mock_transactional_emails.send_transac_email.return_value = mock_response
    mock_client.transactional_emails = mock_transactional_emails
    
    with patch.object(BrevoSender, 'create_client', return_value=mock_client), \
         patch('outreach_module.brevo.email_sending.get_unsubscribe_footer', return_value=" unsub_footer"), \
         patch('outreach_module.brevo.email_sending.SendTransacEmailRequestSender') as mock_sender_req, \
         patch('outreach_module.brevo.email_sending.SendTransacEmailRequestToItem') as mock_to_item:
        
        await sender.send_email(
            to="test@example.com",
            subject="Test Subject",
            content="Test Content",
            unsubscribe_token="token123"
        )
        
        mock_transactional_emails.send_transac_email.assert_called_once()
        # Verify arguments passed to send_transac_email
        args, kwargs = mock_transactional_emails.send_transac_email.call_args
        assert kwargs['subject'] == "Test Subject"
        assert "Test Content" in kwargs['html_content']
        assert "unsub_footer" in kwargs['html_content']
