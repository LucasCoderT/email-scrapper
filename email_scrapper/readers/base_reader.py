import datetime
import logging
import typing

from email_scrapper import utils
from email_scrapper.models import Stores, Order
from email_scrapper.stores import lego, ebgames, walmart, amazon
from email_scrapper.stores.bestbuy import BestBuyReader

logger = logging.getLogger(__name__)


class BaseReader:

    def __init__(self, user_email: str = None, date_from: datetime.datetime = None,
                 email_mapping: typing.Dict[Stores, str] = None):
        self.stores: typing.Dict[Stores, typing.List[Order]] = {}
        self.email = user_email
        if date_from:
            self.search_date_range = date_from
        else:
            self.search_date_range = datetime.datetime.now() - datetime.timedelta(days=7)
        self._store_mapping: typing.Mapping[Stores, typing.Callable] = {
            Stores.AMAZONCA: self.get_amazon_ca,
            Stores.BESTBUYCA: self.get_best_buy,
            Stores.EBGAMES: self.get_ebgames,
            Stores.LEGOCA: self.get_lego,
            Stores.WALMART: self.get_walmart
        }
        self._orders: typing.Dict[str, Order] = {}
        self._email_mapping = email_mapping or {}

    def _get_search_date_range(self):
        return self.search_date_range.strftime(
            "%d-%b-%Y")

    def _get_store(self, store: Stores) -> typing.Optional[typing.List[Order]]:
        func = self._store_mapping.get(store)
        if func:
            return func()
        else:
            return None

    def read_store_emails(self, store: Stores, subject: str = None) -> typing.Iterable[str]:
        raise NotImplemented

    def _save_order(self, order: Order):
        if order.id in self._orders:
            _order = self._orders.get(order.id)
            _order += order
        else:
            self._orders[order.id] = order

    def _finish(self):
        raise NotImplemented

    def _login(self):
        raise NotImplementedError

    def run(self) -> typing.List[Order]:
        self._login()
        return_data = []
        stores = [store for store in Stores]
        for store in stores:
            store_data = self._get_store_email(store)
            if store_data:
                return_data.extend(store_data)
        self._finish()
        return return_data

    def _get_user_email(self) -> str:
        return self.email

    def get_amazon_ca(self) -> typing.List[Order]:
        return self._email_processor(Stores.AMAZONCA, amazon.get_data)

    def get_best_buy(self) -> typing.List[Order]:
        return self._email_processor(Stores.BESTBUYCA, BestBuyReader().save_attachment, "ship")

    def get_ebgames(self) -> typing.List[Order]:
        return self._email_processor(Stores.EBGAMES, ebgames.parse_ebgames_email)

    def get_lego(self) -> typing.List[Order]:
        return self._email_processor(Stores.LEGOCA, lego.parse_lego_email)

    def get_walmart(self) -> typing.List[Order]:
        return self._email_processor(Stores.WALMART, walmart.parse_walmart_email, "shipped")

    def _get_search_query(self, store: Stores, subject: str = None):
        email_address = self._get_store_email(store)
        if subject:
            subject = f"SUBJECT {subject}"
        search_query_list = [
            f"FROM '{email_address}'",
            subject,
            f"SINCE {self._get_search_date_range()}",
            f"TO {self._get_user_email()}"
        ]
        search_query = f"({' '.join(q for q in search_query_list if q)})"
        return search_query

    def _get_store_email(self, store: Stores) -> str:
        """

        Parameters
        ----------
        store :class:Stores

        Returns
        -------
        the email of the store that the reader will filter by

        """
        if self._email_mapping:
            email = self._email_mapping.get(store)
            if email:
                return email
        else:
            return utils.get_store_email(store).value

    def _email_processor(self, store: Stores, processor: typing.Callable[[str], Order], subject: str = None) -> \
            typing.List[Order]:
        logger.log(logging.INFO, f"Processing {store}")
        self._orders.clear()
        for msg_body in self.read_store_emails(store, subject):
            try:
                new_order = processor(msg_body)
                if len(new_order) > 0:
                    self._save_order(new_order)
            except TypeError:
                continue
            except Exception as e:
                logger.log(logging.ERROR, e)
                continue
        else:
            self.stores[store] = list(self._orders.values())
        return self.stores[store]
