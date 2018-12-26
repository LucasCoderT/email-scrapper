from email_scrapper.models import Stores, StoreEmail

store_email_mapping = {
    Stores.AMAZONCA: StoreEmail.AMAZONCA,
    Stores.BESTBUYCA: StoreEmail.BESTBUYCA,
    Stores.EBGAMES: StoreEmail.EBGAMES,
    Stores.LEGOCA: StoreEmail.LEGOCA,
    Stores.WALMART: StoreEmail.WALMART
}


def get_store_email(store: Stores) -> StoreEmail:
    return store_email_mapping[store]
