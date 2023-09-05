# IMPORTATIONS
import datetime
import json
import logging
from math import floor

import pandas as pd
import io
from degiro_connector.trading.api import API as TradingAPI
from degiro_connector.trading.models.trading_pb2 import Credentials, Order, CashAccountReport, ProductsInfo

# SETUP LOGGING LEVEL
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',)

# SETUP CONFIG DICT
with open("/home/patelrajnath/degiro-connector/config/config.json") as config_file:
    config_dict = json.load(config_file)

# SETUP CREDENTIALS
int_account = config_dict.get("int_account")
username = config_dict.get("username")
password = config_dict.get("password")
totp_secret_key = config_dict.get("totp_secret_key")
one_time_password = config_dict.get("one_time_password")

credentials = Credentials(
    int_account=int_account,
    username=username,
    password=password,
    totp_secret_key=totp_secret_key,
    one_time_password=one_time_password,
)

# SETUP TRADING API
trading_api = TradingAPI(credentials=credentials)

# ESTABLISH CONNECTION
trading_api.connect()


# Compute Balance
# SETUP REQUEST
today = datetime.date.today()
from_date = CashAccountReport.Request.Date(
    year=today.year,
    month=today.month,
    day=1,
)
to_date = CashAccountReport.Request.Date(
    year=today.year,
    month=today.month,
    day=today.day,
)
request = CashAccountReport.Request(
    format=CashAccountReport.Format.CSV,
    country="FR",
    lang="fr",
    from_date=from_date,
    to_date=to_date,
)

# FETCH DATA
cash_account_report = trading_api.get_cash_account_report(
    request=request,
    raw=False,
)
# format = cash_account_report.Format.Name(cash_account_report.format)
content = cash_account_report.content
df = pd.read_csv(io.StringIO(content), sep=",", names=['Date','Time','Value date','Product','ISIN','Description','FX','Change','Balance','Order ID'])
current_balance = df.Balance[1]

# Get the closePrice
# SETUP REQUEST
request = ProductsInfo.Request()
request.products.extend([16238669])

# FETCH DATA
products_info = trading_api.get_products_info(
    request=request,
    raw=True,
)

# DISPLAY PRODUCTS_INFO
# print(products_info['data'].get('16238669').get('closePrice'))
bid_price = products_info['data'].get('16238669').get('closePrice') + 0.5
units = floor(current_balance/bid_price)
if units:
    # SETUP ORDER
    order = Order(
        action=Order.Action.BUY,
        order_type=Order.OrderType.LIMIT,
        price=bid_price,
        product_id=16238669,
        size=units,
        time_type=Order.TimeType.GOOD_TILL_DAY,
    )

    # FETCH CHECKING_RESPONSE
    checking_response = trading_api.check_order(order=order)

    # EXTRACT CONFIRMATION_ID
    confirmation_id = checking_response.confirmation_id

    # EXTRACT OTHER DATA
    free_space_new = checking_response.free_space_new
    response_datetime = checking_response.response_datetime
    transaction_fees = checking_response.transaction_fees
    transaction_opposite_fees = checking_response.transaction_opposite_fees
    transaction_taxes = checking_response.transaction_taxes

    # SEND CONFIRMATION
    confirmation_response = trading_api.confirm_order(
        confirmation_id=confirmation_id, order=order
    )

    logging.info(checking_response)
    logging.info(confirmation_response)
else:
    logging.info(f'No sufficient balance to by even a single unit')
    logging.info(f'current_balance:{current_balance}, bid_price:{bid_price}, possible to buy units:{units}')
