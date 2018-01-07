import html
import re
from bs4 import BeautifulSoup
import datetime

global_remover = re.compile("(=(?<==)(.*?)(?=\s))", flags=re.DOTALL)


def parse_email(email):
    soup = BeautifulSoup(str(email), "lxml")
    email_date = email.get("date")
    try:

        order_date = datetime.datetime.strptime(email_date, "%d %b %Y %H:%M:%S %z").strftime("%m/%d/%Y")
    except Exception as e:
        order_date = datetime.datetime.strptime(email_date, "%a, %d %b %Y %H:%M:%S %z").strftime("%m/%d/%Y")
    table_fields = {0: "Sku", 1: "Item", 2: "Platform", 3: "quantity", 4: "price"}
    order_number = None
    items = []
    quantities = []
    prices = []
    cart = []
    all_td_tags = soup.find_all("td")
    all_p_tags = soup.find_all("p")
    for row in all_p_tags[2:]:
        if "Order number" in row.text:
            first_search = re.search(r"(?s)=0A(.*?)\|", row.text) or re.search(r"(?<=\=0A)(.*?)(?=\=7C)", row.text)
            order_number = re.search(r"(\d{2,})", first_search.group(0))
            if order_number is not None:
                order_number = order_number.group(0)
            else:
                print(order_number)
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
        cart.append((item, "${:,.2f}".format(price), quantity, "${:,.2f}".format(unit_price)))

    if order_number is not None:
        return {
            "date": order_date,
            "order_number": order_number,
            "items": cart,
            "discounts": "${:,.2f}".format(0)
        }
    else:
        return {}
