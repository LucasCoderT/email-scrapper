import datetime
import email
import imaplib
import traceback
import typing
from collections import Counter

import openpyxl

from src.email_settings import Email
from src.models import Order, Item
from src.stores import lego, ebgames
from src.stores.amazon import get_data
from src.stores.bestbuy import BestBuyReader


def store_to_dict(store_data: typing.List[Order]) -> list:
    return [dict(order) for order in store_data]


# noinspection PyBroadException
class Reader:

    def __init__(self, username: str, password: str, settings: Email,
                 locations: typing.Dict[str, str] = None,
                 search_range: typing.Tuple[datetime.datetime, datetime.datetime] = None):
        self.username = username
        self.current_date = search_range or (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
        self.mail = imaplib.IMAP4_SSL(*settings.value)
        self.email_locations = locations
        self.stores: typing.Dict[str, typing.List[Order]] = {}
        self.mail.login(username, password)
        self.mail.select('inbox')

    def get_amazon(self):
        if self.email_locations.get("amazonca"):
            print(f"Processing Amazon")
            self.stores["amazonca"] = []
            emails_missed = 0
            self.mail.select(self.email_locations.get("amazonca"))
            try:
                # search and return uids instead
                result, amazon_data = self.mail.uid('search', None,
                                                    f"(FROM 'shipment-tracking@amazon.ca' SINCE {self.current_date} TO '{self.username}')")
                for num in amazon_data[0].split():
                    m, v = self.mail.uid("fetch", num, "(RFC822)")
                    msg_body = email.message_from_bytes(v[0][1])
                    # await add_new_item(await get_data(msg_body))
                    try:
                        email_data = get_data(msg_body)
                        self.stores['amazonca'].append(email_data)
                    except Exception as e:
                        print(e)
                        print(traceback.format_tb(e.__traceback__))
                        emails_missed += 1
                        continue
            except:
                print(f"No folder with the name {self.email_locations['amazonca']} found")
                return

    def get_best_buy(self):
        if self.email_locations.get("bestbuy"):
            print(f"Processing BestBuy")

            self.stores["bestbuy"] = []
            self.mail.select(self.email_locations.get("bestbuy"))
            try:
                # search and return uids instead
                result, bestbuy_data = self.mail.uid('search', None,
                                                     f"(FROM 'noreply@bestbuy.ca' SINCE {self.current_date})")
                for num in bestbuy_data[0].split():
                    m, v = self.mail.uid("fetch", num, "(RFC822)")
                    msg_body = email.message_from_bytes(v[0][1])
                    try:
                        if "ship" in msg_body.get("subject").lower():
                            email_data = BestBuyReader().save_attachment(msg_body)
                            if len(email_data) > 0:
                                self.stores['bestbuy'].append(email_data)
                    except Exception as e:
                        print(e)
                        continue
            except:
                print(f"No folder with the name {self.email_locations['bestbuy']} found")
                return
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

    def get_ebgames(self):
        if self.email_locations.get("ebgames"):
            print(f"Processing EBGames")

            self.stores["ebgames"] = []
            self.mail.select(self.email_locations.get('ebgames'))
            try:
                # search and return uids instead
                result, ebgames_data = self.mail.uid('search', None,
                                                     f"(FROM 'help@ebgames.ca' SINCE {self.current_date})")
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
                        print(e)
                        continue
            except:
                print(f"No folder with the name {self.email_locations['ebgames']} found")
                return

    def get_lego(self):
        if self.email_locations.get("lego"):
            print(f"Processing Lego")
            self.stores["lego"] = []
            self.mail.select(self.email_locations.get("lego"))
            try:
                # search and return uids instead
                result, lego_data = self.mail.uid('search', None,
                                                  f"(FROM 'legoshop@e.lego.com' SINCE {self.current_date})")
                for num in lego_data[0].split():
                    m, v = self.mail.uid("fetch", num, "(RFC822)")
                    msg_body = email.message_from_bytes(v[0][1])
                    # await add_new_item(await get_data(msg_body))
                    try:
                        email_data = lego.parse_lego_email(msg_body)
                        if len(email_data) > 0:
                            self.stores['lego'].append(email_data)
                    except Exception as e:
                        print(e)
                        continue
            except:
                print(f"No folder with the name {self.email_locations['lego']} found")
                return

    def finish(self):
        self.mail.logout()

    def save_to_excel(self):
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

    def run(self) -> dict:
        stores = [getattr(self, store_var) for store_var in dir(self) if
                  store_var.startswith("get_") and callable(getattr(self, store_var))]
        for store_func in stores:
            store_func()
        return self.stores
