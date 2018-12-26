import base64
import datetime
import email
import imaplib
import logging
import typing
from email.message import Message

from email_scrapper.email_settings import Email
from email_scrapper.models import Order, Stores
from email_scrapper.stores import lego, ebgames, walmart, amazon
from email_scrapper.stores.bestbuy import BestBuyReader
from email_scrapper import utils


def store_to_dict(store_data: typing.List[Order]) -> list:
    if store_data:
        return [dict(order) for order in store_data]
    return []


logger = logging.getLogger(__name__)


class Reader:

    def __init__(self, username: str, password: str, settings: Email = Email.GMAIL, email_address: str = None,
                 locations: typing.Dict[Stores, str] = None,
                 date_from: datetime.datetime = None):
        """

        :param username: The SMTP username to log in with
        :param password:  The SMTP password to log in with
        :param settings:  The SMTP settings. Defaults to GMAIL
        :param email_address: The email address that will be looked for using the TO header. Defaults to username if
            not specified
        :param locations: Optional labels to look under
        :param date_from: How far back to search emails from. Default to 7 days.
        """
        self.email = email_address or username
        self.username = username
        if date_from:
            self.search_date_range = date_from
        else:
            self.search_date_range = datetime.datetime.now() - datetime.timedelta(days=31)
        self.search_date_range = self.search_date_range.strftime(
            "%d-%b-%Y")
        self.mail = imaplib.IMAP4_SSL(*settings.value)
        self.stores: typing.Dict[Stores, typing.List[Order]] = {}
        self.email_locations = locations or {}
        self.mail.login(username, password)
        self.mail.select('inbox')

    def _get_emails(self, store: Stores, processor: typing.Callable, subject: str = None) -> typing.List[Order]:
        logger.log(logging.INFO, f"Processing {store}")
        orders: typing.Dict[Order, Order] = {}
        location = self.email_locations.get(store)
        email_address = utils.get_store_email(store)
        if subject:
            subject = f"SUBJECT {subject}"
        if location:
            self.mail.select(location)
        search_query_list = [
            f"FROM '{email_address.value}'",
            subject,
            f"SINCE {self.search_date_range}",
            f"TO {self.email}"
        ]
        search_query = f"({' '.join(q for q in search_query_list if q)})"
        result, amazon_data = self.mail.uid('search', None, search_query)
        try:
            for num in amazon_data[0].split():
                m, v = self.mail.uid("fetch", num, "(RFC822)")
                msg_body = email.message_from_bytes(v[0][1])
                try:
                    order = processor(msg_body)
                    if len(order) > 0:
                        if order.id in orders:
                            o = orders.get(order.id)
                            o += order
                        else:
                            orders[order.id] = order
                except TypeError:
                    continue
                except Exception as e:
                    logger.log(logging.ERROR, e)
                    continue
        finally:
            self.stores[store] = list(orders.values())
        return self.stores[store]

    def get_amazon(self) -> typing.List[Order]:
        return self._get_emails(Stores.AMAZONCA, amazon.get_data)

    def get_best_buy(self) -> typing.List[Order]:
        return self._get_emails(Stores.BESTBUYCA, BestBuyReader().save_attachment, "ship")

    def get_ebgames(self) -> typing.List[Order]:
        return self._get_emails(Stores.EBGAMES, ebgames.parse_ebgames_email)

    def get_lego(self) -> typing.List[Order]:
        return self._get_emails(Stores.LEGOCA, lego.parse_lego_email)

    def get_walmart(self) -> typing.List[Order]:
        return self._get_emails(Stores.WALMART, walmart.parse_walmart_email, "shipped")

    def finish(self):
        self.mail.logout()

    def run(self) -> typing.List[Order]:
        return_data = []
        stores = [getattr(self, store_var) for store_var in dir(self) if
                  store_var.startswith("get_") and callable(getattr(self, store_var))]
        for store_func in stores:
            store_data = store_func()
            if store_data:
                return_data.extend(store_data)
        self.finish()
        return return_data
