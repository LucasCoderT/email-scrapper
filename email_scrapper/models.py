import datetime
import typing
from enum import Enum, auto


class Stores(Enum):
    AMAZONCA = auto()
    AMAZONCOM = auto()
    BESTBUYCA = auto()
    BESTBUYCOM = auto()
    LEGOCA = auto()
    WALMART = auto()
    EBGAMES = auto()


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

    def __len__(self):
        return len(self.cart)

    def __lt__(self, other):
        return self.purchased < other.date

    def __gt__(self, other):
        return self.purchased > other.date

    def __hash__(self):
        return int(self.order_number.replace("-", ""))

    def __eq__(self, other):
        same_order = self.order_number = other.order_number
        same_cart = self.cart == other.cart
        return all([same_order, same_cart])

    def __getitem__(self, item):
        return self.__dict__[item]

    def __add__(self, other):
        self.cart += other.cart

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
