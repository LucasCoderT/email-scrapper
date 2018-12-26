import datetime
import html
import logging
import re

from bs4 import BeautifulSoup

from email_scrapper.models import Order, Item, Stores

global_remover = re.compile("(=(?<==)(.*?)(?=\\s))", flags=re.DOTALL)

logger = logging.getLogger(__name__)


def does_item_exist(items, item):
    try:
        item = item.group(0)
    except:
        item = item

    for i in items:
        if item.replace(" ", "") == i.replace(" ", ""):
            return True
    else:
        return False


def get_data(email):
    email = str(email)
    soup = BeautifulSoup(email, "lxml")
    order_number = re.search(r'(?<=Order\s#)(\d*-\d*-\d*)', email).group(1)
    date = datetime.datetime.strptime(re.findall(r'(Date:.*)', email)[1][6:], "%a, %d %b %Y %H:%M:%S %z")
    items = []
    order_discount = 0.00
    item_quanitites = []
    prices = [p.text for p in soup.find_all("strong") if "CDN" in p.text]
    cart = []
    discounts = set(re.findall("-CDN\$\s.*", email))
    for discount in discounts:
        try:
            amount = float(discount[6:])
        except:
            amount = 0
        order_discount += amount

    item_names = [td.text for td in [td.find("a") for td in soup.find_all("td") if re.search(r"(Sold)", td.text)
                                     or re.search(r"(S=\nold)", td.text)] if len(td.text) > 5]

    for index, link in enumerate(item_names):
        tmp = re.sub(global_remover, "", link)
        tmp = re.sub("\n", "", tmp)
        possible_items = re.sub(r"(\s{2,})", " ", tmp)
        possible_items = re.sub(r"CDN\$ \d+\.\d+", "", possible_items)
        possible_items = possible_items.split("  ")
        if len(possible_items) > 1 and re.search(r"(\d+)(?=([Xx])?)", possible_items[0]):
            for it in possible_items:
                try:
                    item_name = re.search(r"(\dx)(?<=\dx)(.*)(?=Sold)", it)
                    if item_name is not None:
                        item_name = item_name.group(2)
                    else:
                        item_name = re.sub(r"\d+x", "", it)
                except Exception as e:
                    print(e)
                if not does_item_exist(items, item_name):
                    items.append(html.unescape(re.sub(r"\s{2,}", "", item_name)))
                else:
                    continue
                item_quantity = re.search(r"(\d+)(?=([Xx])(=)?)", it)
                if item_quantity:
                    try:
                        item_quanitites.append(int(item_quantity.group(0)))
                    except:
                        item_quanitites.append(1)
                else:
                    item_quanitites.append(1)
        else:
            item_name = re.sub("\n", "", tmp)
            item_name = re.sub(r"(=a.*)", "", item_name)
            item_name = html.unescape(item_name)
            if not does_item_exist(items, item_name):
                item_quantity = re.search(r"(\d+)(?=([Xx])(=)?)", tmp)
                if item_quantity:
                    try:
                        item_quanitites.append(int(item_quantity.group(0)))
                    except:
                        item_quanitites.append(1)
                else:
                    item_quantity = re.search(r"(\d+)(?=([Xx])(=)?)", item_name)
                    if item_quantity:
                        item_quanitites.append(int(item_quantity.group(0)))
                    else:
                        item_quanitites.append(1)
                item_name = re.sub(r'(\d+)(?=([Xx])(=)?)([Xx])', "", item_name)
                item_name = re.sub(r"(<.*?>)", "", item_name)
                item_name = re.sub(r"CDN\$ \d+\.\d+", "", item_name)
                items.append(html.unescape(re.sub(r"\s{2,}", "", item_name)))
            else:
                continue
    for item, price, quantity in zip(items, prices, item_quanitites):
        item = re.sub(r"(Sold by Amazon\.com\.ca, [Ii]nc\. )", "", item)
        item = re.sub(r"(Sold by Amazon\.com\.ca, [Ii]nc\.)", "", item)
        item = re.sub(r"(<.*?>)", "", item)
        if quantity == 0:
            quantity = 10
        formated_price = re.search(r'(\d+.\d+)', price) or re.search(r"(\d+.\d+.\d+)", price)
        try:
            total_price = float(formated_price.group(0).replace(",", ""))
            try:
                unit_price = round(total_price / quantity, 2)
            except ZeroDivisionError:
                unit_price = total_price
            cart.append(Item(item, unit_price, quantity, order_number))
        except Exception as e:
            logger.log(logging.ERROR, e)

    rdata = Order(order_number, date, Stores.AMAZONCA, cart, discount=order_discount)
    return rdata
