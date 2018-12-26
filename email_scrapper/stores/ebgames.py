import datetime
import html
import re

from bs4 import BeautifulSoup

from email_scrapper.models import Order, Item, Stores

global_remover = re.compile("(=(?<==)(.*?)(?=\\s))", flags=re.DOTALL)


def parse_ebgames_email(email):
    soup = BeautifulSoup(str(email), "lxml")
    email_date = email.get("date")
    try:

        order_date = datetime.datetime.strptime(email_date, "%d %b %Y %H:%M:%S %z")
    except Exception as e:
        order_date = datetime.datetime.strptime(email_date, "%a, %d %b %Y %H:%M:%S %z")
    table_fields = {0: "Sku", 1: "Item", 2: "Platform", 3: "quantity", 4: "price"}
    order_number = None
    items = []
    quantities = []
    prices = []
    cart = []
    all_td_tags = soup.find_all("td")
    all_p_tags = soup.find_all("p")
    order_discount = 0.00
    discounts = set(re.findall("-CDN\$\s.*", str(email)))
    for discount in discounts:
        try:
            amount = float(discount[6:])
        except:
            amount = 0
        order_discount += amount
    for row in all_p_tags[2:]:
        if "Order number" in row.text:
            first_search = re.search(r"(?s)=0A(.*?)\|", row.text) or re.search(r"(?<=\=0A)(.*?)(?=\=7C)", row.text)
            order_number = re.search(r"(\d{2,})", first_search.group(0))
            if order_number is not None:
                order_number = order_number.group(0)
    for index, row in enumerate(all_td_tags):
        text = html.unescape(row.text)
        if index - 5 == 0:
            continue
        elif index - 5 == 1:
            items.append(re.sub(global_remover, "", text))
        elif index - 5 == 2:
            continue
        elif index - 5 == 3:
            try:
                quantities.append(int(text))
            except:
                quantities.append(1)
        elif index - 5 == 4:
            _ = re.sub("=2E", ".", text)
            _ = re.sub(global_remover, "", _)
            prices.append(float(re.sub("\\n", "", _)))

    for item, quantity, price in zip(items, quantities, prices):
        try:
            unit_price = float(int(price) / int(quantity))
        except ZeroDivisionError:
            unit_price = float(price)
        cart.append(Item(item, unit_price, quantity, order_number))

    if order_number is not None:
        return Order(order_number, order_date, Stores.EBGAMES,cart,discount=order_discount)
    else:
        return None
