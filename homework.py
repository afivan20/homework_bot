import logging
import telegram
import os
from dotenv import load_dotenv
import time
import requests
from logging import StreamHandler
import sys
from json import JSONDecodeError


load_dotenv()

TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('ID')
PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
PRACTICUM_ENDPOINT = (
    'https://practicum.yandex.ru/api/user_api/homework_statuses/'
)
PRACTICUM_HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}
RETRY_TIME = 300

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='homework.log',
)
logger = logging.getLogger(__name__)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)

try:
    BOT = telegram.Bot(token=TELEGRAM_TOKEN)
except Exception as critical:
    logging.critical(
        f'Отсутствие обязательных переменных окружения '
        f'во время запуска бота. {critical}'
    )


class UnexpectedResponse(Exception):
    """Логгирование при статусе ответа отличном от 200."""

    logging.error(
        f'Эндпоинт {PRACTICUM_ENDPOINT} недоступен. '
    )
    pass


def get_api_answer(url, current_timestamp):
    """Отправляем запрос к API домашки на эндпоинт."""
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=PRACTICUM_HEADERS, params=payload)
    except requests.exceptions.RequestException as error:
        logging.error(f'Невозможно получит ответ от сервера, ошибка - {error}')
        return {}
    if response.status_code != 200:
        message = (
            f'Эндпоинт {PRACTICUM_ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
        send_message(BOT, message)
        raise UnexpectedResponse(message)
    try:
        return response.json()
    except JSONDecodeError as err:
        logging.error(f'Не возможно прочиатать json ответ, ошибка - {err}')
        return {}


def check_response(response):
    """Проверим есть ли появился ли статус ДЗ."""
    homeworks = response.get('homeworks')
    homework = homeworks[0]
    return parse_status(homework)


def parse_status(homework):
    """Проанализируем статус домашки и найдем вердикт ревьюера."""
    try:
        verdict = HOMEWORK_STATUSES[homework['status']]
    except KeyError as error:
        message = (f'Такого статуса не существует. Ошибка {error}')
        logging.error(message)
        return send_message(BOT, message)
    homework_name = homework['homework_name']
    if verdict:
        message = (
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )
    return send_message(BOT, message)


def send_message(bot, message):
    """Отправляем сообщение пользователю."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logging.error(
            f'Невозможно отправить сообщение пользователю, ошибка - {error}'
        )


def main():
    """Запускаем телеграм-бот для проверки статуса ДЗ."""
    current_timestamp = int(time.time())
    from_date = (current_timestamp - RETRY_TIME * 2)
    while True:
        try:
            api = get_api_answer(
                PRACTICUM_ENDPOINT,
                from_date
            )
            check_response(api)
            time.sleep(RETRY_TIME)
        except Exception:
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
