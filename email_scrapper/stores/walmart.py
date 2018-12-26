import base64
import datetime
import re

from bs4 import BeautifulSoup

from email_scrapper.models import Order, Stores, Item


def parse_walmart_email(msg_body):
    msg_body: bytes = base64.b64decode(msg_body.get_payload()[0]._payload)
    email = str(msg_body.decode("utf-8"))
    soup = BeautifulSoup(email, "lxml")
    order_items = soup.find_all("table", {"cellpadding": "5", "cellspacing": "0"})[0].find_all("tr", {"valign": "top"})[
                  1:]
    date = datetime.datetime.strptime(soup.find_all("orderdate")[0].text, "%B %d, %Y")
    order_number = soup.find_all("ordernumber")[0].text
    cart = []
    order_discount = 0.00
    discounts = set(re.findall("-CDN\$ .*", email))
    for discount in discounts:
        try:
            amount = float(discount[6:])
        except:
            amount = 0
        order_discount += amount
    for item in order_items:
        name = item.select("itemname")[0].text
        quantity = float(item.select("quantity")[0].text)
        unit_price = float(item.select("price")[0].text[1:])
        cart.append(Item(name, unit_price, int(quantity), order_number))
    order = Order(order_number, date, Stores.WALMART, cart)
    return order
