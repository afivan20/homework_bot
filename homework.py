import logging
import telegram
import os
from dotenv import load_dotenv
import time
import requests
from logging import StreamHandler
import sys


load_dotenv()

PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('ID')
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

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def send_message(bot, message):
    """Отправляем сообщение пользователю."""
    bot.send_message(chat_id=CHAT_ID, text=message)
    message_info = (
        f'Сообщение: "{message}" доставлено пользователю {CHAT_ID}'
    )
    logging.info(message_info)


def get_api_answer(url, current_timestamp):
    """Отправляем запрос к API домашки на эндпоинт."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    response = requests.get(url, headers=headers, params=payload)
    if response.status_code != 200:
        message = (
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
        send_message(BOT, message)
        raise logging.error(
            message)
    response = requests.get(url, headers=headers, params=payload).json()
    try:
        check_response(response)
    except Exception:
        pass
    return response


def parse_status(homework):
    """Проанализируем статус домашки и найдем вердикт ревьюера."""
    try:
        verdict = HOMEWORK_STATUSES[homework['status']]
    except Exception as error:
        message = (f'Такого статуса не существует. Ошибка {error}')
        logging.error(message)
        send_message(BOT, message)
    homework_name = homework["homework_name"]
    print(f'Изменился статус проверки работы "{homework_name}". {verdict}')
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        send_message(bot, message)
    except Exception:
        logging.critical('AAAA')
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверим есть ли появился ли статус ДЗ."""
    homeworks = response.get('homeworks')
    homework = homeworks[0]
    try:
        status = homeworks[0].get('status')
    except Exception as error:
        message = (f'Статус домашнего задания не найден! {error}')
        logging.error(message)
        send_message(BOT, message)
    parse_status(homework)
    return status


def main():
    """Запускаем телеграм-бот для проверки статуса ДЗ."""
    if (TELEGRAM_TOKEN is None) or (CHAT_ID) is None:
        logging.critical(
            'Отсутствуют обязательные переменная окружения:'
            ' "PRACTICUM_TOKEN" Программа принудительно остановлена.')

    current_timestamp = int(time.time())
    while True:
        try:
            get_api_answer(ENDPOINT, current_timestamp - RETRY_TIME * 2)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(BOT, message)
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
