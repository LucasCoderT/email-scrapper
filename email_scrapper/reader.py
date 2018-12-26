import base64
import datetime
import email
import imaplib
import logging
import typing
from email.message import Message

from email_scrapper.email_settings import Email
from email_scrapper.models import Order, Stores
from email_scrapper.stores import lego, ebgames, walmart
from email_scrapper.stores.amazon import get_data
from email_scrapper.stores.bestbuy import BestBuyReader


def store_to_dict(store_data: typing.List[Order]) -> list:
    if store_data:
        return [dict(order) for order in store_data]
    return []


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
            self.search_date_range = datetime.datetime.now() - datetime.timedelta(days=31)
        self.search_date_range = self.search_date_range.strftime(
            "%d-%b-%Y")
        self.mail = imaplib.IMAP4_SSL(*settings.value)
        self.stores: typing.Dict[Stores, typing.List[Order]] = {}
        self.email_locations = locations or {}
        self.mail.login(username, password)
        self.mail.select('inbox')

    def get_amazon(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing Amazon")
        orders: typing.Dict[Order, Order] = {}
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
                    order = get_data(msg_body)
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
        except Exception as e:
            logger.log(logging.ERROR, e)
            return []
        finally:
            self.stores[Stores.AMAZONCA] = list(orders.values())
        return self.stores[Stores.AMAZONCA]

    def get_best_buy(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing BestBuy")
        orders: typing.Dict[Order, Order] = {}
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
                order = BestBuyReader().save_attachment(msg_body)
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
        self.stores[Stores.BESTBUYCA] = list(orders.values())
        return self.stores[Stores.BESTBUYCA]

    def get_ebgames(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing EBgames")

        orders: typing.Dict[Order, Order] = {}
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
                        order = ebgames.parse_ebgames_email(msg_body)
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
        except:
            return []
        finally:
            self.stores[Stores.EBGAMES] = list(orders.values())
        return self.stores[Stores.EBGAMES]

    def get_lego(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing Lego")
        orders: typing.Dict[Order, Order] = {}
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
                    order = lego.parse_lego_email(msg_body)
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
        except Exception as e:
            logger.log(logging.ERROR, e)
            return []
        finally:
            self.stores[Stores.LEGOCA] = list(orders.values())
        return self.stores[Stores.LEGOCA]

    def get_walmart(self) -> typing.List[Order]:
        logger.log(logging.INFO, "Processing Walmart")
        orders: typing.Dict[Order, Order] = {}
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

                    msg_body: bytes = base64.b64decode(msg_body.get_payload()[0]._payload)
                    order = walmart.parse_walmart_email(msg_body.decode("utf-8"))
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
        except Exception as e:
            logger.log(logging.ERROR, e)
            return []
        finally:
            self.stores[Stores.WALMART] = list(orders.values())
        return self.stores[Stores.WALMART]

    def process_order(self, order):
        pass

    def finish(self):
        self.mail.logout()

    def save_to_excel(self):
        import openpyxl
        workbook = openpyxl.Workbook()
        workbook.guess_types = True
        del workbook['Sheet']
        for store in self.stores:
            sheet = workbook.create_sheet(title=store.name)
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
