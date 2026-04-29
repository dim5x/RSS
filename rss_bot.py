import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import configparser
from difflib import SequenceMatcher
import logging
from logging.handlers import RotatingFileHandler
import time
from threading import Thread

from bs4 import BeautifulSoup
from flask import Flask, send_from_directory
import defusedxml.ElementTree as ElemTree  # Заменил стандартный парсер на безопасную версию.
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

OUT_URL = 'https://lenta.ru/rss'
LOCAL_URL = "http://192.168.0.101:5000/images/"
FALLBACK_URL = LOCAL_URL + "fallback.jpg"
IMAGE_LIST = []
PATH_FOR_IMAGES = os.getcwd() + '\\images\\'


from collections import deque

dq = deque(maxlen=200)

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


# def parse_text(url: str) -> str:
#     """
#     Parses the text content from the given URL and returns it.
#
#     Parameters:
#         url (str): The URL of the article to parse
#
#     Returns:
#         str: The parsed text content
#
#     """
#     if url is None: return ''
#     article = Article(url, language='ru')  # Create Article object for the given URL
#     article.download()  # Download the article content
#     article.parse()  # Parse the article
#
#     # If no text is extracted, return an empty string
#     if not article.text:
#         return ''
#
#     # Clean up the text content
#     article_text = article.text.replace('\n\n', '\n')
#     article_text = article_text.split('\n')[1:]  # Remove the title
#
#     # Add period at the end of each line if not present
#     article_text = [line + '.' if line and not line.endswith('.') else line for line in article_text]
#
#     try:
#         # Check similarity between the first two lines and remove if similar
#         similarity = sim(article_text[0], article_text[1])
#         if similarity >= 0.3:
#             article_text = article_text[1:]
#     except Exception:
#         logging.exception('Ошибка')
#
#     # Find and remove the last line containing 'Ранее'
#     ind = max([i for i, line in enumerate(article_text) if 'Ранее' in line], default=50)
#     article_text = '\n'.join(line for line in article_text[:ind] if line)  # Join non-empty lines with newline
#
#     return article_text

def parse_text(url:str) -> str:
    if url is None: return ''
    text = ''
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # titles = soup.find(class_='topic-body__title').text
        # image = soup.find(class_='picture__image')['src']
        content = soup.find_all(class_='topic-body__content-text')
        text = ''.join([i.text for i in content if "Ранее" not in i.text])
    except Exception as e:
        logging.exception('from parse_text')

    return text




def fetch_rss_feed(url) -> None:
    """Download and save RSS feed."""
    print('Try download and save RSS feed. (def fetch_rss_feed())')
    try:
        with requests.get(url, timeout=5) as response:
            response.raise_for_status()
            with open('lenta.xml', 'wb') as f:
                f.write(response.content)
        logging.info('Successfully fetched Lenta RSS.')

    except Exception:
        logging.exception(f'from fetch_rss_feed({url})')


def download_image(dq):
    if not dq:
        return

    list_of_files = set(os.listdir(PATH_FOR_IMAGES))
    print(f'{list_of_files=}')
    print(len(list_of_files))
    # dif = set([filename.split('/')[-1] for filename in dq]).difference(list_of_files)
    dif = [i for i in dq if i.split('/')[-1] not in list_of_files]

    print(f'{dif=}')
    print(len(dif))
    # breakpoint()

    for url in dif:
        # namefile = url.split('/')[-1]
        # если уже скачано — используем
        # if os.path.exists(f'images/{namefile}'):
        #     continue
        # url = OUT_URL + filename
        try:
            logging.info(f'Downloading {url}')
            r = requests.get(url, timeout=(5, 10), headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            with open(f'{PATH_FOR_IMAGES}{url.split('/')[-1]}', 'wb') as f:
                f.write(r.content)
                logging.info(f'Successfully downloaded image.')
            time.sleep(2)

        except Exception:
            logging.exception(f"download_image failed: {url}")

    # global IMAGE_LIST
    # IMAGE_LIST = []
    logging.info('Downloading images done.')

def process_item(item):
    try:
        # Извлекаем:
        category = item.findtext('category', default='')
        if category in ('Путешествия', 'Спорт'):
            return
            # item.remove('category')
        title = item.findtext('title', default='')
        print(title)

        link = item.findtext('link', default='')
        image_url = item.find('enclosure').get('url')
        if image_url.endswith('.jpg'):
            IMAGE_LIST.append(image_url)
            dq.append(image_url)
        local_image_url = LOCAL_URL + image_url.split('/')[-1]
        for element in list(item):
            if element.tag in ('author', 'category', 'guid', 'enclosure'):
                item.remove(element)
            if element.tag == 'description' and len(element.text) < 10:
                # element.text = f'{parse_text(link)}'  # Parse and update description if condition is met
                img_html = f'<img src="{local_image_url}" style="width:100%; height:auto; display:block; margin-bottom:10px;" />'
                element.text = f'<![CDATA[{img_html}{parse_text(link)}]]>'
            # if element.tag == 'enclosure':
                # element.set('url', local_image_url)

    except Exception:
        logging.exception(f"Ошибка:")


def process_xml_content():
    tree = ElemTree.parse('lenta.xml')  # Parse the XML file
    root = tree.getroot()  # Get the root of the XML tree
    items = list(root.iter("item"))

    clear_items_dict = {}
    for item in items:
    # for item in items[10]:
        title = item.findtext('title')
        if item.findtext('category') in ('Путешествия', 'Спорт'):
            continue
        if title in clear_items_dict:
            continue
        clear_items_dict[title] = item

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(process_item, item) for item in clear_items_dict.values()]
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
            fetch_rss_feed(OUT_URL)

            # 2. Parse and process XML.
            process_xml_content()

            end = time.time()
            mes = f'Elapsed time: {end - start}'
            logging.info(mes)

            if IMAGE_LIST:
                logging.info('Downloading images...')
                thread2 = Thread(target=download_image(dq))
                thread2.start()
                print(thread2.is_alive())

        except Exception as e:
            logging.exception(e)

        time.sleep(60 * 60)  # Wait 1 hour


thread1 = Thread(target=parse_lenta_rss)
thread1.start()

app = Flask(__name__)


@app.route('/')
def index_route() -> str:
    """A function that returns a message based on whether a thread is alive."""
    message = '&#128994;' if thread1.is_alive() else '&#128308;'
    return message


@app.route('/rss')
def rss_route():
    with open('output.xml', 'r', encoding='utf-8') as f:
        rss = f.readlines()
    return ''.join(rss)  # rss


@app.route("/images/<path:filename>")
def images_route(filename):
    return send_from_directory("images", filename, mimetype="image/jpeg")


if __name__ == '__main__':
    host = config['settings']['host']
    port = config['settings'].getint('port')
    app.run(debug=False, host=host, port=port)
