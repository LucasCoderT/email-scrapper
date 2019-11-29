import typing

from email_scrapper.models import Stores, StoreEmail, Order

store_email_mapping = {
    Stores.AMAZONCA: StoreEmail.AMAZONCA,
    Stores.BESTBUYCA: StoreEmail.BESTBUYCA,
    Stores.EBGAMES: StoreEmail.EBGAMES,
    Stores.LEGOCA: StoreEmail.LEGOCA,
    Stores.WALMART: StoreEmail.WALMART
}


def get_store_email(store: Stores) -> StoreEmail:
    return store_email_mapping[store]


def store_to_dict(store_data: typing.List["Order"]) -> list:
    if store_data:
        return [dict(order) for order in store_data]
    return []
