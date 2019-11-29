import datetime
import logging
import typing

from email_scrapper import utils
from email_scrapper.models import Stores, Order
from email_scrapper.stores import lego, ebgames, walmart, amazon
from email_scrapper.stores.bestbuy import BestBuyReader

logger = logging.getLogger(__name__)


class BaseReader:

    def __init__(self, user_email: str = None, date_from: datetime.datetime = None):
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

    def get_search_date_range(self):
        return self.search_date_range.strftime(
            "%d-%b-%Y")

    def get_store(self, store: Stores) -> typing.Optional[typing.List[Order]]:
        func = self._store_mapping.get(store)
        if func:
            return func()
        else:
            return None

    def read_store_emails(self, store: Stores, subject: str = None) -> typing.Iterable[str]:
        raise NotImplemented

    def save(self):
        raise NotImplemented

    def finish(self):
        raise NotImplemented

    def run(self):
        raise NotImplemented

    def get_user_email(self) -> str:
        return self.email

    def get_amazon_ca(self) -> typing.List[Order]:
        return self.email_processor(Stores.AMAZONCA, amazon.get_data)

    def get_best_buy(self) -> typing.List[Order]:
        return self.email_processor(Stores.BESTBUYCA, BestBuyReader().save_attachment, "ship")

    def get_ebgames(self) -> typing.List[Order]:
        return self.email_processor(Stores.EBGAMES, ebgames.parse_ebgames_email)

    def get_lego(self) -> typing.List[Order]:
        return self.email_processor(Stores.LEGOCA, lego.parse_lego_email)

    def get_walmart(self) -> typing.List[Order]:
        return self.email_processor(Stores.WALMART, walmart.parse_walmart_email, "shipped")

    def get_search_query(self, store: Stores, subject: str = None):
        email_address = self.get_store_email(store)
        if subject:
            subject = f"SUBJECT {subject}"
        search_query_list = [
            f"FROM '{email_address}'",
            subject,
            f"SINCE {self.get_search_date_range()}",
            f"TO {self.get_user_email()}"
        ]
        search_query = f"({' '.join(q for q in search_query_list if q)})"
        return search_query

    def get_store_email(self, store: Stores) -> str:
        return utils.get_store_email(store).value

    def email_processor(self, store: Stores, processor: typing.Callable[[str], Order], subject: str = None) -> \
            typing.List[Order]:
        logger.log(logging.INFO, f"Processing {store}")
        orders: typing.Dict[str, Order] = {}
        for msg_body in self.read_store_emails(store, subject):
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
        else:
            self.stores[store] = list(orders.values())
        return self.stores[store]
