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
PATH_FOR_IMAGES = os.path.join(os.getcwd(), 'images')

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

def parse_text(url: str) -> str:
    if not url: return ''
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = session.get(url, headers=headers, timeout=30, verify=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.find_all(class_='topic-body__content-text')
        text = ' '.join([i.text for i in content if "Ранее" not in i.text])
        return text
    except Exception as e:
        logging.exception('Exception in parse_text')
        return ''


def fetch_rss_feed(url) -> bool:
    """Download and save RSS feed."""
    logging.info('Downloading RSS feed...')
    try:
        with requests.get(url, timeout=5) as response:
            response.raise_for_status()
            with open('lenta.xml', 'wb') as f:
                f.write(response.content)
        logging.info('Successfully fetched Lenta RSS.')
        return True
    except Exception:
        logging.exception(f'Exception in fetch_rss_feed({url})')
        return False

def download_image(url: str) -> None:
    """Download single image."""
    try:
        filename = url.split('/')[-1]
        filepath = os.path.join(PATH_FOR_IMAGES, filename)

        # Skip if already exists
        if os.path.exists(filepath):
            logging.info(f'Image already exists: {filename}')
            return

        logging.info(f'Downloading image: {filename}')
        response = requests.get(url, timeout=(5, 10), headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

        logging.info(f'Successfully downloaded: {filename}')

    except Exception:
        logging.exception(f"Failed to download image: {url}")


def download_images_from_queue():
    """Download images from queue."""
    if not dq:
        logging.info('No images to download')
        return

    # Get unique images not already downloaded
    existing_files = set(os.listdir(PATH_FOR_IMAGES))
    images_to_download = [
        url for url in dq
        if url.split('/')[-1] not in existing_files
    ]

    if not images_to_download:
        logging.info('All images already downloaded')
        return

    logging.info(f'Downloading {len(images_to_download)} images...')

    # Download images in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download_image, url) for url in images_to_download]
        for future in as_completed(futures):
            future.result()  # This will raise any exceptions

    logging.info('Image download completed')



# def download_image(dq):
#     if not dq:
#         return
#
#     list_of_files = set(os.listdir(PATH_FOR_IMAGES))
#     print(f'{list_of_files=}')
#     print(len(list_of_files))
#     # dif = set([filename.split('/')[-1] for filename in dq]).difference(list_of_files)
#     dif = [i for i in dq if i.split('/')[-1] not in list_of_files]
#
#     print(f'{dif=}')
#     print(len(dif))
#     # breakpoint()
#
#     for url in dif:
#         # namefile = url.split('/')[-1]
#         # если уже скачано — используем
#         # if os.path.exists(f'images/{namefile}'):
#         #     continue
#         # url = OUT_URL + filename
#         try:
#             logging.info(f'Downloading {url}')
#             r = requests.get(url, timeout=(5, 10), headers={"User-Agent": "Mozilla/5.0"})
#             r.raise_for_status()
#             path = os.path.join(PATH_FOR_IMAGES, url.split('/')[-1])
#             with open(path, 'wb') as f:
#                 f.write(r.content)
#                 logging.info(f'Successfully downloaded image.')
#             time.sleep(2)
#
#         except Exception:
#             logging.exception(f"download_image failed: {url}")
#
#     # global IMAGE_LIST
#     # IMAGE_LIST = []
#     logging.info('Downloading images done.')


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
                # img_html = f'<img src="{local_image_url}"/>'
                # print(img_html)
                # element.text = fr'<![CDATA[{img_html}{parse_text(link)}]]>'
                cdata_content = f'{img_html}</br>{parse_text(link)}'
                element.text = cdata_content

            # if element.tag == 'enclosure':
            #     element.set('url', local_image_url)

    except Exception:
        logging.exception(f"Ошибка:")


def process_xml_content():
    tree = ElemTree.parse('lenta.xml')  # Parse the XML file
    root = tree.getroot()  # Get the root of the XML tree
    items = list(root.iter("item"))

    clear_items_dict = {}
    try:
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
        logging.info(f'RSS parsed successfully! Processed {len(clear_items_dict)} items.')
        return True

    except Exception:
        logging.exception("Error processing XML content")
        return False

def parse_lenta_rss() -> None:
    """Function to parse the RSS feed from Lenta.ru."""
    while True:
        start = time.time()
        try:
            # 1. Fetch RSS.
            if not fetch_rss_feed(OUT_URL):
                time.sleep(60)
                continue

            # 2. Parse and process XML.
            if not process_xml_content():
                time.sleep(60)
                continue


            mes = f'Elapsed time: {time.time() - start}'
            logging.info(mes)

            if dq:
                logging.info('Starting background image download...')
                # download_thread = Thread(target=download_images_from_queue, daemon=True)
                download_thread = Thread(target=download_images_from_queue)
                download_thread.start()
                print(download_thread.is_alive())

        except Exception as e:
            logging.exception(f'Unexpected error in main loop: {e}')

        time.sleep(60 * 60)  # Wait 1 hour


rss_thread = Thread(target=parse_lenta_rss)
rss_thread.start()

app = Flask(__name__)


@app.route('/')
def index_route() -> str:
    """A function that returns a message based on whether a thread is alive."""
    status = '&#128994;' if rss_thread.is_alive() else '&#128308;'
    return status


@app.route('/rss')
def rss_route():
    try:
        with open('output.xml', 'r', encoding='utf-8') as f:
            rss = f.readlines()
        return ''.join(rss)  # rss
    except FileNotFoundError:
        return 'output.xml not available', 404

@app.route("/images/<path:filename>")
def images_route(filename):
    try:
        return send_from_directory("images", filename, mimetype="image/jpeg")
    except FileNotFoundError:
        return 'File not found', 404

if __name__ == '__main__':
    host = config['settings']['host']
    port = config['settings'].getint('port')

    logging.info(f'Starting Flask server on {host}:{port}')
    app.run(debug=False, host=host, port=port)
