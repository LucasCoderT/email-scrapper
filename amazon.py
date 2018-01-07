import datetime
import html
import re
from bs4 import BeautifulSoup

discount_methods = {"3for30": re.compile(r'(3 for \$30.*)'), "prime savings": re.compile('(Prime Savings .*)'),
                    "gifting discount": re.compile(r"(Gifting Discount .*)")}
global_remover = re.compile("(=(?<==)(.*?)(?=\s))", flags=re.DOTALL)


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


async def get_data(email):
    soup = BeautifulSoup(email, "lxml")
    order_number = re.search(r'(?<=Order\s#)(\d*-\d*-\d*)', email).group(1)
    date = datetime.datetime.strptime(re.findall(r'(Date:.*)', email)[1][6:], "%a, %d %b %Y %H:%M:%S %z").strftime(
        "%m/%d/%Y")
    items = []
    order_discount = {}
    item_quanitites = []
    prices = [p.text for p in soup.find_all("strong") if "CDN" in p.text]
    cart = []
    for method, pattern in discount_methods.items():
        discount_method = re.findall(pattern, email)
        for _ in discount_method:
            content = _.split()
            order_discount[method] = float(content[-1])
            break

    item_names = [td.text for td in soup.find_all("td") if
                  re.search(r"(Sold)", td.text) or re.search(r"(S=\nold)", td.text)]
    for index, link in enumerate(item_names):
        var = re.search(r"(Sold)", link) or re.search(r"(S=\nold)", link)
        if var:
            tmp = re.sub(global_remover, "", link)
            tmp = re.sub("\n", "", tmp)
            tmp = re.search(r"(\dx)(?<=\dx)(.*)(?=Sold)", tmp)
            if tmp is not None:
                possible_items = re.sub(r"(\s{2,})", " ", tmp.group(0))
                possible_items = re.sub(r"CDN\$ \d+\.\d+", "", possible_items)
                possible_items = possible_items.split("  ")
                if len(possible_items) > 1 and re.search(r"(\d+)(?=([Xx])(\=)?)", possible_items[0]):
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
                        item_quantity = re.search(r"(\d+)(?=([Xx])(\=)?)", it)
                        if item_quantity:
                            try:
                                item_quanitites.append(int(item_quantity.group(0)))
                            except:
                                item_quanitites.append(1)
                        else:
                            item_quanitites.append(1)
                else:
                    item_name = re.sub(r"(Sold by Amazon\.com\.ca, [Ii]nc\. )", "", tmp.group(2))
                    item_name = re.sub("\n", "", item_name)
                    item_name = re.sub(r"(\=a.*)", "", item_name)
                    item_name = html.unescape(item_name)
                    if not does_item_exist(items, item_name):
                        item_quantity = re.search(r"(\d+)(?=([Xx])(\=)?)", tmp.group(1))
                        if item_quantity:
                            try:
                                item_quanitites.append(int(item_quantity.group(0)))
                            except:
                                item_quanitites.append(1)
                        else:
                            item_quantity = re.search(r"(\d+)(?=([Xx])(\=)?)", item_name)
                            if item_quantity:
                                item_quanitites.append(int(item_quantity.group(0)))
                            else:
                                item_quanitites.append(1)
                        item_name = re.sub(r'(\d+)(?=([Xx])(\=)?)', "", item_name)
                        item_name = re.sub(r"(<.*?>)", "", item_name)
                        item_name = re.sub(r"CDN\$ \d+\.\d+", "", item_name)
                        items.append(html.unescape(re.sub(r"\s{2,}", "", item_name)))
                    else:
                        continue
            else:
                tmp = re.sub(global_remover, "", link)
                item_name = re.sub("\n", "", tmp)
                item_name = re.sub(r"(\=a.*)", "", item_name)
                item_name = re.sub(r"\s{2,}", " ", item_name)
                item_name = re.search(r"(\dx)(?<=\dx)(.*)(?=Sold)", item_name) or re.search(r"(.*)(?=Sold)",
                                                                                            item_name)
                item_name = re.sub(r"(Sold by Amazon\.com\.ca, [Ii]nc\. )", "", item_name.group(0))
                item_name = re.sub(r"(<.*?>)", "", item_name)
                item_name = html.unescape(re.sub(r"\s{2,}", "", item_name))
                item_name = re.sub(r"CDN\$ \d+\.\d+", "", item_name)
                if not does_item_exist(items, item_name):
                    item_quantity = re.search(r"(\d+)(?=([Xx])(\=)?)", item_name)
                    if item_quantity:
                        try:
                            item_quanitites.append(int(item_quantity.group(0)))
                        except:
                            item_quanitites.append(1)
                    else:
                        item_quanitites.append(1)

                    items.append(item_name)

    for item, price, quantity in zip(items, prices, item_quanitites):
        item = re.sub(r"(Sold by Amazon\.com\.ca, [Ii]nc\. )", "", item)
        item = re.sub(r"(Sold by Amazon\.com\.ca, [Ii]nc\.)", "", item)
        item = re.sub(r"(<.*?>)", "", item)
        if quantity == 0:
            quantity = 10
        formated_price = re.search(r'(\d+.\d+)', price) or re.search(r"(\d+.\d+.\d+)", price)
        try:
            total_price = float(formated_price.group(0).replace(",", ""))
        except Exception as e:
            print(e)
        try:
            unit_price = round(total_price / quantity, 2)
        except ZeroDivisionError:
            unit_price = total_price
        cart.append((item, "${:,.2f}".format(total_price), quantity, "${:,.2f}".format(unit_price)))

    rdata = {
        "items": cart,
        "order_number": order_number,
        "date": date,
        "discounts": "${:,.2f}".format(sum(order_discount.values()))
    }
    return rdata
