# Add unsubscribe footer to email content
def get_unsubscribe_footer(server_url: str, unsubscribe_token: str) -> str:
    return f"""
<br><br>
<hr style="border: 1px solid #ddd;">
<p style="font-size: 12px; color: #666;">
    If you no longer wish to receive these emails, 
    <a href="{server_url}/unsubscribe?token={unsubscribe_token}">
        click here to unsubscribe
    </a>.
</p>
"""