import datetime
import email
import imaplib
import logging
import typing
from collections import Counter
import base64
from email.message import Message

from email_scrapper.email_settings import Email
from email_scrapper.models import Order, Item, Stores
from email_scrapper.stores import lego, ebgames, walmart
from email_scrapper.stores.amazon import get_data
from email_scrapper.stores.bestbuy import BestBuyReader


def store_to_dict(store_data: typing.List[Order]) -> list:
    return [dict(order) for order in store_data]


logger = logging.getLogger(__name__)


# noinspection PyBroadException
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
            self.search_date_range = datetime.datetime.now() - datetime.timedelta(days=7)
        self.search_date_range = self.search_date_range.strftime(
                "%d-%b-%Y")
        self.mail = imaplib.IMAP4_SSL(*settings.value)
        self.email_locations = locations or {}
        self.stores: typing.Dict[str, typing.List[Order]] = {}
        self.mail.login(username, password)
        self.mail.select('inbox')

    def get_amazon(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing Amazon")
        self.stores["amazonca"] = []
        location = self.email_locations.get(Stores.AMAZONCA)
        if self.email_locations.get(Stores.AMAZONCA):
            self.mail.select(location)
        try:
            # search and return uids instead
            result, amazon_data = self.mail.uid('search', None,
                                                f"(FROM 'shipment-tracking@amazon.ca' SINCE {self.search_date_range} "
                                                f"TO '{self.email}')")
            for num in amazon_data[0].split():
                m, v = self.mail.uid("fetch", num, "(RFC822)")
                msg_body = email.message_from_bytes(v[0][1])
                # await add_new_item(await get_data(msg_body))
                try:
                    email_data = get_data(msg_body)
                    self.stores['amazonca'].append(email_data)
                except:
                    continue
        except Exception as e:
            logger.log(logging.ERROR, e)
            return []
        return self.stores['amazonca']

    def get_best_buy(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing BestBuy")
        self.stores["bestbuy"] = []
        location = self.email_locations.get(Stores.BESTBUYCA)
        if self.email_locations.get(Stores.BESTBUYCA):
            self.mail.select(location)
        # search and return uids instead
        result, bestbuy_data = self.mail.uid('search', None,
                                             f"(FROM 'noreply@bestbuy.ca' SUBJECT 'ship' SINCE {self.search_date_range} "
                                             f"TO '{self.email}')")
        for num in bestbuy_data[0].split():
            m, v = self.mail.uid("fetch", num, "(RFC822)")
            msg_body = email.message_from_bytes(v[0][1])
            try:
                email_data = BestBuyReader().save_attachment(msg_body)
                if len(email_data) > 0:
                    self.stores['bestbuy'].append(email_data)
            except Exception as e:
                logger.log(logging.ERROR, e)
                continue

        orders_cleaned: typing.List[str] = []
        for order in self.stores['bestbuy']:
            if order.id in orders_cleaned:
                continue
            cart = []
            total_quantity = Counter()
            total_prices = Counter()
            same_order = [o for o in self.stores['bestbuy'] if
                          o.id == order.id]
            if len(same_order) == 1:
                orders_cleaned.append(order.id)
                continue
            for orde in same_order:
                for old_order in orde.cart:
                    total_quantity[old_order.name] += old_order.quantity
                    total_prices[old_order.name] += old_order.unit_price
            for item, quantity in total_quantity.items():
                new_unit_price = total_prices[item] / quantity
                cart.append(Item(item, new_unit_price, total_quantity[item],
                                 order_id=order.id))
            order.cart = cart
            orders_cleaned.append(order.id)
        return self.stores['bestbuy']

    def get_ebgames(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing EBgames")

        self.stores["ebgames"] = []
        location = self.email_locations.get(Stores.EBGAMES)
        if self.email_locations.get(Stores.EBGAMES):
            self.mail.select(location)
        try:
            # search and return uids instead
            result, ebgames_data = self.mail.uid('search', None,
                                                 f"(FROM 'help@ebgames.ca' SINCE {self.search_date_range} "
                                                 f"TO '{self.email}')")
            for num in ebgames_data[0].split():
                m, v = self.mail.uid("fetch", num, "(RFC822)")
                msg_body = email.message_from_bytes(v[0][1])
                # await add_new_item(await get_data(msg_body))
                try:
                    if "Shipment" in msg_body.get("subject"):
                        email_data = ebgames.parse_ebgames_email(msg_body)
                        if len(email_data) > 0:
                            self.stores['ebgames'].append(email_data)
                except Exception as e:
                    logger.log(logging.ERROR, e)
                    continue
        except:
            return []
        return self.stores['ebgames']

    def get_lego(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing Lego")
        self.stores["lego"] = []
        location = self.email_locations.get(Stores.LEGOCA)
        if self.email_locations.get(Stores.LEGOCA):
            self.mail.select(location)
        try:
            # search and return uids instead
            result, lego_data = self.mail.uid('search', None,
                                              f"(FROM 'legoshop@e.lego.com' SINCE {self.search_date_range} "
                                              f"TO '{self.email}')")
            for num in lego_data[0].split():
                m, v = self.mail.uid("fetch", num, "(RFC822)")
                msg_body = email.message_from_bytes(v[0][1])
                # await add_new_item(await get_data(msg_body))
                try:
                    email_data = lego.parse_lego_email(msg_body)
                    if len(email_data) > 0:
                        self.stores['lego'].append(email_data)
                except Exception as e:
                    logger.log(logging.ERROR, e)
                    continue
        except Exception as e:
            logger.log(logging.ERROR, e)
            return []
        return self.stores['lego']

    def get_walmart(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing Walmart")
        self.stores["walmart"] = []
        location = self.email_locations.get(Stores.WALMART)
        if self.email_locations.get(Stores.WALMART):
            self.mail.select(location)
        try:
            # search and return uids instead
            result, walmart_data = self.mail.uid('search', None,
                                                 f"(FROM 'noreply@walmart.ca' SUBJECT 'shipped' SINCE {self.search_date_range} "
                                                 f"TO '{self.email}')")
            for num in walmart_data[0].split():
                m, v = self.mail.uid("fetch", num, "(RFC822)")
                msg_body: Message = email.message_from_bytes(v[0][1])
                # await add_new_item(await get_data(msg_body))
                try:

                    msg_body = base64.b64decode(msg_body.get_payload()[0]._payload)
                    email_data = walmart.parse_walmart_email(msg_body.decode("utf-8"))
                    if len(email_data) > 0:
                        self.stores['walmart'].append(email_data)
                except Exception as e:
                    logger.log(logging.ERROR, e)
                    continue
        except Exception as e:
            logger.log(logging.ERROR, e)
            return []
        return self.stores['walmart']

    def finish(self):
        self.mail.logout()

    def save_to_excel(self):
        import openpyxl
        workbook = openpyxl.Workbook()
        workbook.guess_types = True
        del workbook['Sheet']
        for store in self.stores:
            sheet = workbook.create_sheet(title=store)
            for order in sorted(self.stores[store]):
                for item in order.cart:
                    row = [order.purchased, order.id]
                    row.extend(item)
                    row.append(order.discount)
                    try:
                        sheet.append(row)
                    except Exception as e:
                        print(e)
                        continue
        workbook.save(f"{self.username}-{datetime.datetime.now().strftime('%d-%m-%y')}.xlsx")
        print(f'Analyzed {sum([len(store_email) for store_email in self.stores.values()])} emails')

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
