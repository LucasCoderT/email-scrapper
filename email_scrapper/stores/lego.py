import datetime
import html
import re

from bs4 import BeautifulSoup

from email_scrapper.models import Order, Item, Stores

global_remover = re.compile("(=(?<==)(.*?)(?=\\s))", flags=re.DOTALL)


def parse_lego_email(email) -> Order:
    soup = BeautifulSoup(str(email), "lxml")
    if re.search("Order Confirmation", soup.text):
        email_date = email.get("date")
        try:

            order_date = datetime.datetime.strptime(email_date, "%d %b %Y %H:%M:%S %z")
        except Exception as e:
            order_date = datetime.datetime.strptime(email_date, "%a, %d %b %Y %H:%M:%S %z")
        order_number = None
        items = []
        cart = []
        prices = []
        quantites = []
        order_discount = 0.00
        discounts = set(re.findall("-CDN\$\s.*", str(email)))
        for discount in discounts:
            try:
                amount = float(discount[6:])
            except:
                amount = 0
            order_discount += amount
        all_td_tags = soup.find_all("td")
        for index, data in enumerate(all_td_tags):
            text = re.sub("\t", "", html.unescape(data.text))
            if index in [1, 2, 3, 4]:
                continue
            if "Order Number" in text:
                first_search = re.search("(T.*)", text)
                order_number = first_search.group(0)
                break

        item_names = soup.find_all("td", attrs={"class": "3D=22padT15=22"})
        for item in item_names:
            name = re.sub(global_remover, "", item.text)
            name = re.sub("\n", "", name)
            name = " ".join([r.group(0) for r in re.finditer("(\d*?\w+)", name)])
            items.append(name)
            continue
        item_prices = soup.find_all("td", attrs={"class": "3D=22w50pc"})
        for price in item_prices:
            text = price.text
            if re.search("Qty", text):
                quantites.append(re.search(r"\d+", text).group(0))
                continue
            _ = re.sub("=2E", ".", text)
            _ = re.sub(global_remover, "", _)
            item_price = re.search("(\d+.\d+)", _)
            prices.append(float(item_price.group(0)))

        for item, quantity, price in zip(items, quantites, prices):
            try:
                unit_price = float(price) / float(quantity)
            except ZeroDivisionError:
                unit_price = float(price)
            cart.append(
                Item(item, unit_price, int(quantity), order_number))

        return Order(order_number, order_date, Stores.LEGOCA, cart, discount=order_discount)

    return None
