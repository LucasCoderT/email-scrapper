import datetime
import email
import imaplib
import json
import traceback
from collections import Counter

import openpyxl

import ebgames
import lego
from amazon import get_data
from bestbuy import save_attachment
from order import Order


class EmailReader:

    def __init__(self, user, username, password, host, port, **kwargs):
        self.current_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
        self.mail = imaplib.IMAP4_SSL(host=host, port=port)
        self.email_locations = kwargs.get("locations")
        self.user = user
        self.mail.login(username, password)
        self.stores = {}
        self.mail.select('inbox')
        self.workbook = openpyxl.Workbook()

    def get_amazon(self):
        if self.email_locations.get("amazonca"):
            print(f"Processing Amazon")
            self.stores["amazonca"] = []
            emails_missed = 0
            self.mail.select(self.email_locations.get("amazonca"))
            try:
                # search and return uids instead
                result, data = self.mail.uid('search', None,
                                             f"(FROM 'shipment-tracking@amazon.ca' SINCE {self.current_date})")
                for num in data[0].split():
                    m, v = self.mail.uid("fetch", num, "(RFC822)")
                    msg_body = email.message_from_bytes(v[0][1])
                    # await add_new_item(await get_data(msg_body))
                    try:
                        email_data = await get_data(msg_body)
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
                result, data = self.mail.uid('search', None,
                                             f"(FROM 'noreply@bestbuy.ca' SINCE {self.current_date})")  # search and return uids instead
                for num in data[0].split():
                    m, v = self.mail.uid("fetch", num, "(RFC822)")
                    msg_body = email.message_from_bytes(v[0][1])
                    try:
                        if "ship" in msg_body.get("subject").lower():
                            email_data = save_attachment(msg_body)
                            if len(email_data) > 0:
                                self.stores['bestbuy'].append(email_data)
                    except Exception as e:
                        print(e)
                        continue
            except:
                print(f"No folder with the name {self.email_locations['bestbuy']} found")
                return
            orders_cleaned = []
            new_orders = []
            for order in self.stores['bestbuy']:
                if order['order_number'] in orders_cleaned:
                    continue
                cart = []
                total_quantity = Counter()
                total_prices = Counter()
                same_order = [o for o in self.stores['bestbuy'] if
                              o.order_number == order.order_number]
                if len(same_order) == 1:
                    formated_cart = []
                    orders_cleaned.append(order.order_number)
                    for item in order.cart:
                        formated_cart.append((item[0], "${:,.2f}".format(item[1]), item[2], "${:,.2f}".format(item[3])))
                    new_orders.append(Order(order._date, order.order_number, formated_cart))
                    continue
                for orde in same_order:
                    for old_order in orde.cart:
                        total_quantity[old_order[0]] += old_order[2]
                        total_prices[old_order[0]] += old_order[1]
                for item, quantity in total_quantity.items():
                    new_unit_price = total_prices[item] / quantity
                    cart.append(
                        (item, "${:,.2f}".format(total_prices[item]), total_quantity[item],
                         "${:,.2f}".format(new_unit_price))
                    )
                new_orders.append(Order(order._date, order.order_number, cart))
                orders_cleaned.append(order.order_number)
            self.stores['bestbuy'] = new_orders

    def get_ebgames(self):
        if self.email_locations.get("ebgames"):
            print(f"Processing EBGames")

            self.stores["ebgames"] = []
            self.mail.select(self.email_locations.get('ebgames'))
            try:
                result, data = self.mail.uid('search', None,
                                             f"(FROM 'help@ebgames.ca' SINCE {self.current_date})")  # search and return uids instead
                for num in data[0].split():
                    m, v = self.mail.uid("fetch", num, "(RFC822)")
                    msg_body = email.message_from_bytes(v[0][1])
                    # await add_new_item(await get_data(msg_body))
                    try:
                        if "Shipment" in msg_body.get("subject"):
                            email_data = ebgames.parse_email(msg_body)
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
                result, data = self.mail.uid('search', None,
                                             f"(FROM 'legoshop@e.lego.com' SINCE {self.current_date})")  # search and return uids instead
                for num in data[0].split():
                    m, v = self.mail.uid("fetch", num, "(RFC822)")
                    msg_body = email.message_from_bytes(v[0][1])
                    # await add_new_item(await get_data(msg_body))
                    try:
                        email_data = lego.parse_email(msg_body)
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

    def save_to_file(self):
        self.workbook.guess_types = True
        del self.workbook['Sheet']
        for store in self.stores:
            sheet = self.workbook.create_sheet(title=store)
            for order in sorted(self.stores[store]):
                for item in order.cart:
                    row = [order.date, order.order_number]
                    row.extend(item)
                    row.append(order.discounts)
                    try:
                        sheet.append(row)
                    except Exception as e:
                        print(e)
                        continue
        self.workbook.save(f"{self.user}-{datetime.datetime.now().strftime('%d-%m-%y')}.xlsx")
        print(f"Analyzed {sum([len(store) for store in self.stores.values()])} emails")

    def save(self):
        return self.stores

    def run(self,to_file: bool = True) -> dict:
        stores = [getattr(self, store) for store in dir(self) if
                  store.startswith("get_") and callable(getattr(self, store))]
        for store in stores:
            store()
        if to_file:
            self.save_to_file()
        else:
            return self.save()


if __name__ == '__main__':
    readers = []
    with open("accounts.json") as file:
        accounts = json.load(file)
    for account in accounts:
        try:
            reader = EmailReader(account, **accounts[account])
            readers.append(reader)
            print(f"Sucessfully logged into account {account}")
        except Exception as e:
            print(f"Unable to log into account {account} with the credentials provided")
            response = input("Continue with other accounts? [Y/N}")
            if response.upper() == "Y":
                continue
            else:
                exit(0)
    for reader in readers:
        reader.run(False)
