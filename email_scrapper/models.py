import datetime
import typing
from difflib import SequenceMatcher
from enum import Enum, auto


class Stores(Enum):
    AMAZONCA = auto()
    AMAZONCOM = auto()
    BESTBUYCA = auto()
    BESTBUYCOM = auto()
    LEGOCA = auto()
    WALMART = auto()
    EBGAMES = auto()


class StoreEmail(Enum):
    AMAZONCA = "shipment-tracking@amazon.ca"
    BESTBUYCA = "noreploy@bestbuy.ca"
    EBGAMES = "help@ebgames.ca"
    LEGOCA = "legoshop@e.lego.com"
    WALMART = "noreply@walmart.ca"


class Order:

    def __init__(self, order_number: str, purchased: datetime.datetime, store: Stores,
                 cart: typing.List["Item"] = None,
                 tracking: str = None, shipped: bool = None, discount: float = 0.00):
        self.id = order_number
        self.purchased = purchased
        self.store = store
        self.tracking = tracking
        self.shipped = shipped
        self.discount = round(discount, 2)
        self.cart = cart or []

    def __repr__(self):
        return f"{self.id} - {self.store}"

    def __len__(self):
        return len(self.cart)

    def __lt__(self, other):
        return self.purchased < other.date

    def __gt__(self, other):
        return self.purchased > other.date

    def __hash__(self):
        return int(self.id.replace("-", ""))

    def __eq__(self, other):
        same_order = self.id = other.id
        same_cart = self.cart == other.cart
        return all([same_order, same_cart])

    def __getitem__(self, item):
        return self.__dict__[item]

    def __iadd__(self, other: "Order"):
        for item1, item2 in zip(self.cart, other.cart):
            ratio = SequenceMatcher(None, item1.name, item2.name).ratio()
            if ratio > 0.90:
                item1.quantity += item2.quantity

    def __iter__(self):
        iters = dict((x, y) for x, y in Order.__dict__.items() if not x.startswith("_"))
        iters.update(self.__dict__)
        for x, y in iters.items():
            if isinstance(y, list):
                yield x, [dict(item) for item in y]
            elif isinstance(y, Stores):
                yield x, y.value
            elif isinstance(y, datetime.datetime):
                yield x, y.strftime("%Y-%m-%d")
            else:
                yield x, y


class Item:
    def __init__(self, name, unit_price: float, quantity: int, order_id: str, item_page: str = None):
        self.name = name
        self.order = order_id
        self.unit_price = round(unit_price, 2)
        self.quantity = quantity
        self.item_page = item_page

    def __repr__(self):
        return f"<{self.name}> - <{self.order}> - <{self.quantity}> - <{self.unit_price}>"

    def __iter__(self):
        iters = dict((x, y) for x, y in Item.__dict__.items() if not x.startswith("_"))
        iters.update(self.__dict__)
        for x, y in iters.items():
            if isinstance(y, datetime.datetime):
                yield x, y.strftime("%Y-%m-%d")
            else:
                yield x, y

    def __eq__(self, other):
        return self.order == other.order and self.name == other.name

    def __hash__(self):
        return hash(self.name)
