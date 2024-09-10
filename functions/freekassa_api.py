import hashlib
import requests

from urllib.parse import urlencode


class FreeKassaApi:
    def __init__(self, merchant_id, first_secret, second_secret):
        self.base_url = 'https://api.bot-t.com/payment/freekassa'
        self.merchant_id = merchant_id
        self.first_secret = first_secret
        self.second_secret = second_secret

    def generate_payment_link(self, order_id, summ, currency='RUB'):
        """
        Generate payment link for redirecting user to Free-Kassa.com.
        :param order_id: ID заказа
        :param summ: Сумма платежа
        :param currency: Валюта платежа (по умолчанию RUB)
        :return: Ссылка на оплату
        """
        signature_string = f"{self.merchant_id}:{summ}:{self.first_secret}:{currency}:{order_id}"
        signature = hashlib.md5(signature_string.encode('utf-8')).hexdigest()

        params = {
            'm': self.merchant_id,
            'oa': summ,
            'o': order_id,
            's': signature,
            'currency': currency,
            'lang': 'ru'
        }

        return 'https://pay.freekassa.com/?' + urlencode(params)

    def generate_api_signature(self, order_id):
        """Генерация подписи для проверки заказа"""
        signature_string = f"{self.merchant_id}:{order_id}:{self.second_secret}"
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()

    def get_order(self, order_id):
        """Проверяет статус платежа по его order_id"""
        params = {
            'merchant_id': self.merchant_id,
            's': self.generate_api_signature(order_id),
            'action': 'check_order_status',
            'order_id': order_id,
        }

        try:
            # Используем метод GET вместо POST
            response = requests.get(self.base_url, params=params)

            # Печатаем все параметры запроса и ответ сервера для отладки
            print(f"Запрос: {response.url}")
            print(f"HTTP статус: {response.status_code}")
            print(f"Ответ от сервера: {response.text}")

            # Пробуем парсить ответ как JSON
            response_data = response.json()

            if response.status_code == 200:
                return response_data
            else:
                raise Exception(f"Ошибка при запросе статуса платежа: {response_data}")

        except ValueError as ve:
            print(f"Ошибка парсинга JSON: {ve}")
            print(f"Получен ответ: {response.text}")
            return None
        except Exception as e:
            print(f"Ошибка при запросе к API FreeKassa: {e}")
            return None

    def generate_api_signature(self, order_id):
        """Генерация подписи для проверки заказа"""
        signature_string = f"{self.merchant_id}:{order_id}:{self.second_secret}"
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()