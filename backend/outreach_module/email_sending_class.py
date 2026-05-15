from abc import ABC, abstractmethod

class EmailSender(ABC):
    """
    Abstract class for sending emails. Decouples email sending from any specific email sender.
    """

    @abstractmethod
    async def create_client(self, api_key):
        raise NotImplementedError

    @abstractmethod
    async def send_email(self, to: str, frm: str, subject: str, content: str, unsubscribe_token: str):
        """
        Send email. Raise if not called.
        """
        raise NotImplementedError
