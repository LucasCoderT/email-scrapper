import base64
import datetime
import email
import logging
import os
import typing
from email.message import Message

from googleapiclient import errors

from email_scrapper.models import Stores
from email_scrapper.readers.base_reader import BaseReader

logger = logging.getLogger(__name__)


class GmailReader(BaseReader):
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self, service, user_id: str = "me", user_email: str = None, email_mapping: dict = None,
                 date_from: datetime.datetime = None):
        """

        Parameters
        ----------
        service:
        The Gmail API service
        email_mapping: dict
        Mapping of class:Stores: to str representing the email to search from
        """
        super(GmailReader, self).__init__(date_from=date_from, user_email=user_email, email_mapping=email_mapping)
        self.service = service
        self.user_id = user_id

    @classmethod
    def authenticate_with_browser(cls, credentials_json: dict = None, date_from: datetime.datetime = None):
        """
        Login to gmail through the browser.
        Requires a credentials.json file or a credentials_json dict passed

        Returns
        -------
        GmailReader

        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            import pickle
            creds = None

            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if credentials_json:
                    flow = InstalledAppFlow.from_client_config(credentials_json, GmailReader.SCOPES)
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', GmailReader.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            service = build('gmail', 'v1', credentials=creds)
            response = service.users().getProfile(userId="me").execute()
            return cls(service, user_id="me", user_email=response.get("emailAddress"), date_from=date_from)
        except (ImportError, ModuleNotFoundError):
            raise BaseException("Google Auth library not found")

    def _get_search_date_range(self):
        return self.search_date_range.strftime("%Y-%m-%d")

    def _get_email_details(self, message) -> Message:
        response = self.service.users().messages().get(userId=self.user_id, id=message['id'], format="raw").execute()
        msg_str = base64.urlsafe_b64decode(response['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)
        return mime_msg

    def _get_search_query(self, store: Stores, subject: str = None):
        return f"from:{self._get_store_email(store)} after:{self._get_search_date_range()}"

    def read_store_emails(self, store: Stores, subject: str = None) -> typing.Generator[str, None, None]:
        query = self._get_search_query(store, subject)
        try:
            response = self.service.users().messages().list(userId=self.user_id,
                                                            q=query).execute()
            if 'messages' in response:
                for message in response['messages']:
                    yield self._get_email_details(message)
            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = self.service.users().messages().list(userId=self.user_id, q=query,
                                                                pageToken=page_token).execute()
                for message in response['messages']:
                    yield self._get_email_details(message)
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
