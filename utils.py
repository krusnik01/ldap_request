from ldap3 import Server, Connection, SUBTREE
import configparser

AD='LDAP-TestM'

config = configparser.ConfigParser()  # создаём объекта парсера
config.read("settings.ini")  # читаем конфиг
AD_SERVER = config[AD]["AD_SERVER"]
AD_USER = config[AD]["AD_USER"]
AD_PASSWORD = config[AD]["AD_PASSWORD"]
AD_SEARCH_TREE = config[AD]["AD_SEARCH_TREE"]

def get_ldap_info(ad_filter, ad_attributes):
    with Connection(Server(AD_SERVER),
                    auto_bind=True,
                    read_only=True,
                    user=AD_USER, password=AD_PASSWORD) as c:
        return (c.extend.standard.paged_search(search_base=AD_SEARCH_TREE,
                                               search_filter=ad_filter,
                                               search_scope=SUBTREE,
                                               attributes=ad_attributes))


if __name__ == "__main__":
    pass