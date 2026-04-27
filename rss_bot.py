from concurrent.futures import ThreadPoolExecutor, as_completed
import configparser
from difflib import SequenceMatcher
import logging
from logging.handlers import RotatingFileHandler
import time
from threading import Thread, Lock

from flask import Flask
import defusedxml.ElementTree as ElemTree  # Заменил стандартный парсер на безопасную версию.
from newspaper import Article
import requests

# Configure configparser.
config = configparser.ConfigParser()
config.read('config.ini')

# Configure root logger.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a rotating file handler.
file_handler = RotatingFileHandler('error.log', maxBytes=100000, backupCount=2,
                                   encoding='utf-8')  # 100000 bytes = 100 KB
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s \t %(name)s \t %(levelname)s \t %(message)s', datefmt='%d-%m-%Y %H:%M:%S')

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handler to the root logger.
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Убираем ненужные сообщения от werkzeug с Esc-последовательностями.
logging.getLogger("werkzeug").setLevel(logging.ERROR)

URL = 'https://lenta.ru/rss'

# "Кэш".
seen = set()
lock = Lock()


def sim(a: str, b: str) -> float:
    """
    A function that calculates the similarity ratio between two input sequences.

    Parameters:
        a (any): The first input sequence.
        b (any): The second input sequence.

    Returns:
        float: The similarity ratio between the two input sequences.

    """
    return SequenceMatcher(None, a, b).ratio()


def parse_text(url: str) -> str:
    """
    Parses the text content from the given URL and returns it.

    Parameters:
        url (str): The URL of the article to parse

    Returns:
        str: The parsed text content

    """
    if url is None: return ''
    article = Article(url, language='ru')  # Create Article object for the given URL
    article.download()  # Download the article content
    article.parse()  # Parse the article

    # If no text is extracted, return an empty string
    if not article.text:
        return ''

    # Clean up the text content
    article_text = article.text.replace('\n\n', '\n')
    article_text = article_text.split('\n')[1:]  # Remove the title

    # Add period at the end of each line if not present
    article_text = [line + '.' if line and not line.endswith('.') else line for line in article_text]

    try:
        # Check similarity between the first two lines and remove if similar
        similarity = sim(article_text[0], article_text[1])
        if similarity >= 0.3:
            article_text = article_text[1:]
    except Exception:
        logging.exception('Ошибка')

    # Find and remove the last line containing 'Ранее'
    ind = max([i for i, line in enumerate(article_text) if 'Ранее' in line], default=50)
    article_text = '\n'.join(line for line in article_text[:ind] if line)  # Join non-empty lines with newline

    return article_text


def fetch_rss_feed(url) -> None:
    """Download and save RSS feed."""
    try:
        with requests.get(url, timeout=5) as response:
            response.raise_for_status()
            with open('lenta.xml', 'wb') as f:
                f.write(response.content)
        logging.info('Successfully fetched Lenta RSS.')

    except Exception:
        logging.exception(f'from fetch_rss_feed(url)')


def process_item(item):
    # Периодически очищаем кэш.
    if len(seen) > 1000:
        with lock:
            seen.clear()

    try:
        # Извлекаем:
        category = item.findtext('category', default='')
        if category in ('Путешествия', 'Спорт'):
            return

        title = item.findtext('title', default='')
        print(title)

        with lock:
            if title in seen:
                return
            seen.add(title)

        link = item.findtext('link', default='')
        image_url = item.find('enclosure').get('url')

        for element in list(item):
            if element.tag in ('author', 'category', 'guid', 'enclosure'):
                item.remove(element)
            if element.tag == 'description' and len(element.text) < 10:
                element.text = f'<img src="{image_url}"/><br>{parse_text(link)}'  # Parse and update description if condition is met

    except Exception:
        logging.exception(f"Ошибка:")


def process_xml_content():
    tree = ElemTree.parse('lenta.xml')  # Parse the XML file
    root = tree.getroot()  # Get the root of the XML tree
    items = list(root.iter("item"))

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(process_item, item) for item in items]
        for f in as_completed(futures):
            _ = f.result()

    tree.write('output.xml', encoding='utf-8')
    logging.info('RSS parsed successfully!')


def parse_lenta_rss() -> None:
    """Function to parse the RSS feed from Lenta.ru."""
    while True:
        start = time.time()
        try:
            # 1. Fetch RSS.
            fetch_rss_feed(URL)

            # 2. Parse and process XML.
            process_xml_content()

            end = time.time()
            mes = f'Elapsed time: {end - start}'
            logging.info(mes)
        except Exception as e:
            logging.exception(e)

        time.sleep(60 * 60)  # Wait 1 hour


thread = Thread(target=parse_lenta_rss)
thread.start()

app = Flask(__name__)


@app.route('/')
def hello_world() -> str:
    """A function that returns a message based on whether a thread is alive."""
    message = '&#128994;' if thread.is_alive() else '&#128308;'
    return message


@app.route('/rss')
def index():
    with open('output.xml', 'r', encoding='utf-8') as f:
        rss = f.readlines()
    return ''.join(rss)  # rss


if __name__ == '__main__':
    host = config['settings']['host']
    port = config['settings'].getint('port')
    app.run(debug=False, host=host, port=port)
