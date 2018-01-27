import datetime


class Order:

    def __init__(self, date, order_number, cart, discounts=0):
        self.date = date.strftime("%m/%d/%Y")
        self._date = date
        self.order_number = order_number
        self.cart = cart
        self.discounts = "${:,.2f}".format(discounts)

    def __len__(self):
        return len(self.cart)

    def __lt__(self, other):
        return self._date < other._date

    def __gt__(self, other):
        return self._date > other._date

    def __hash__(self):
        return int(self.order_number.replace("-", ""))

    def __eq__(self, other):
        same_order = self.order_number = other.order_number
        same_cart = self.cart == other.cart
        return all([same_order, same_cart])

    def __getitem__(self, item):
        return self.__dict__[item]

