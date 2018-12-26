import datetime
import html
import io
import re

import pdfminer
import pdfminer.high_level
import pdfminer.layout
import pdfminer.settings
from bs4 import BeautifulSoup
from pdfminer.image import ImageWriter

from email_scrapper.models import Order, Item, Stores

pdfminer.settings.STRICT = False


class BestBuyReader:

    def save_attachment(self, msg):
        """
        Given a message, save its attachments to the specified
        download folder (default is /tmp)

        return: file path to attachment
        """
        files = {}
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            try:
                fp = io.BytesIO(part.get_payload(decode=True))
                fp.seek(0)
                files[filename] = fp
            except Exception as e:
                print(e)
                continue
        if len(files) == 0:
            return {}
        converted_data = self.extract_text(files=files, output_type="html")
        return self.parse_pdf(converted_data)

    def extract_text(self, files=None,
                     _py2_no_more_posargs=None,  # Bloody Python2 needs a shim
                     no_laparams=False, all_texts=None, detect_vertical=None,  # LAParams
                     word_margin=None, char_margin=None, line_margin=None, boxes_flow=None,  # LAParams
                     output_type='text', codec='utf-8', strip_control=False,
                     maxpages=0, page_numbers=None, password="", scale=1.0, rotation=0,
                     layoutmode='normal', output_dir=None, debug=False,
                     disable_caching=False, **other):
        if _py2_no_more_posargs is not None:
            raise ValueError("Too many positional arguments passed.")
        if not files:
            raise ValueError("Must provide files to work upon!")

        # If any LAParams group arguments were passed, create an LAParams object and
        # populate with given args. Otherwise, set it to None.
        if not no_laparams:
            laparams = pdfminer.layout.LAParams()
            for param in ("all_texts", "detect_vertical", "word_margin", "char_margin", "line_margin", "boxes_flow"):
                paramv = locals().get(param, None)
                if paramv is not None:
                    setattr(laparams, param, paramv)
        else:
            laparams = None

        imagewriter = None
        if output_dir:
            imagewriter = ImageWriter(output_dir)

        out_files = []

        for fname, fdata in files.items():
            file = io.BytesIO()
            pdfminer.high_level.extract_text_to_fp(fdata, file, **locals())
            file.seek(0)
            out_files.append(file)
        return out_files

    def bs4method(self, raw_data):
        soup = BeautifulSoup(raw_data, "lxml")
        all_spans = soup.find_all("span")
        quantities = []
        items = []
        prices = []
        order_number = None
        cart = []
        item_name = None
        order_date = None
        order_discount = 0.00
        discounts = set(re.findall("-CDN\$\s.*", raw_data))
        for discount in discounts:
            try:
                amount = float(discount[6:])
            except:
                amount = 0
            order_discount += amount

        for index, data in enumerate(all_spans):
            if index == 0:
                continue
            else:
                if "Order Number" in all_spans[index - 1].text:
                    order_number = re.search(r'(\d*)', data.text).group(0)
                elif "Qty" in all_spans[index - 1].text:
                    for qty in re.findall(r"\d+", data.text):
                        quantities.append(int(qty))
                elif "Product Description" in data.text or "Product Description" in all_spans[index - 1].text:
                    if item_name is not None:
                        continue
                    try:
                        tmp_items = re.findall(r"(?s)\n(.*?)\n", data.text)
                        text = data.text.split("\n")
                        if not tmp_items:
                            raise Exception
                        if tmp_items:
                            item_name = tmp_items[0]
                        if "Product Description" in text:
                            item_name = tmp_items[0]
                            raise Exception
                        items.extend(t for t in data.text.split("\n") if t)
                    except:
                        if data.text.strip("\n") in ["Product Description", "Payment Information", "Serial Number"]:
                            continue
                        item_name = html.unescape(
                            item_name.strip("\n") if item_name is not None else data.text.strip("\n"))
                        items.append(item_name)
                elif "Order Date" in data.text:
                    order_date = datetime.datetime.strptime(data.text.strip("\n"),
                                                            "Order Date: %d-%b-%Y %I:%M:%S %p (PST)")
                elif "Total\n" == all_spans[index - 1].text:
                    for total in re.findall(r"\d+.\d+", data.text):
                        prices.append(float(total.replace(",", "")))

        for item, quantity, price in zip(items, quantities, prices):
            try:
                unit_price = float(price) / int(quantity)
            except ZeroDivisionError:
                unit_price = float(price)
            cart.append(Item(item, unit_price, quantity, order_number))

        return Order(order_number, order_date, Stores.BESTBUYCA, cart,discount=order_discount)

    def parse_pdf(self, files: list):
        items = []
        order_date = None
        order_number = None
        for file in files:
            raw_data = file.read().decode("utf-8")
            data = self.bs4method(raw_data)
            if order_date is None:
                order_date = data.purchased
            if order_number is None:
                order_number = data.id
            items.extend(data.cart)

        return Order(order_number, order_date, Stores.BESTBUYCA, items)
