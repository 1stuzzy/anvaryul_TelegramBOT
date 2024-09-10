from flask import Flask, request, abort
from loader import config
import hashlib

app = Flask(__name__)


ALLOWED_IPS = ['168.119.157.136', '168.119.60.227', '178.154.197.79', '51.250.54.238']


def get_client_ip():
    """Получение IP адреса клиента."""
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr


def is_allowed_ip(ip):
    """Проверка, что запрос идет с разрешенного IP."""
    return ip in ALLOWED_IPS


def validate_signature(data):
    """Валидация подписи запроса."""
    sign_string = f"{config.merchant_id}:{data['AMOUNT']}:{config.first_secret}:{data['MERCHANT_ORDER_ID']}"
    generated_sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    return generated_sign == data.get('SIGN')


@app.route('/payment/freekassa', methods=['POST'])
def freekassa_payment_handler():
    # Получаем IP клиента
    client_ip = get_client_ip()

    # Проверка IP
    if not is_allowed_ip(client_ip):
        return abort(403, description="Unauthorized IP address")

    # Проверка подписи
    if not validate_signature(request.form):
        return abort(400, description="Invalid signature")

    # Дополнительные проверки (сумма платежа, статус заказа и т.д.)
    # Например:
    # if not validate_amount(request.form['AMOUNT']):
    #     return abort(400, description="Invalid amount")
    # if is_order_already_processed(request.form['MERCHANT_ORDER_ID']):
    #     return abort(400, description="Order already processed")

    # Если все проверки пройдены, считаем платеж успешным
    # Здесь можно добавить логику обработки успешного платежа

    return "YES"