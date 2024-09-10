from difflib import SequenceMatcher
import logging
from logging.handlers import RotatingFileHandler
import time
from threading import Thread
import xml.etree.ElementTree as ET

from flask import Flask
from newspaper import Article
import requests

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a rotating file handler
handler = RotatingFileHandler('error.log', maxBytes=100000, backupCount=2, encoding='utf-8')  # 100000 bytes = 100 KB
formatter = logging.Formatter('%(asctime)s \t %(name)s \t %(levelname)s \t %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
handler.setFormatter(formatter)

# Add the handler to the root logger
logger.addHandler(handler)



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

    ind = 50
    try:
        # Check similarity between the first two lines and remove if similar
        similarity = sim(article_text[0], article_text[1])
        if similarity >= 0.3:
            article_text = article_text[1:]

        # Find and remove the last line containing 'Ранее'
        ind = max([i for i, line in enumerate(article_text) if 'Ранее' in line])
    except Exception:
        pass

    # Join non-empty lines with newline
    article_text = '\n'.join(line for line in article_text[:ind] if line)

    return article_text


def parse_lenta_rss() -> None:
    """
    Function to parse the RSS feed from Lenta.ru
    """
    while True:
        url = 'https://lenta.ru/rss'
        # Connect
        try:
            response = requests.get(url)
            logging.info('Connected to Lenta!')
            if response.status_code != 200:
                raise Exception('Something went wrong with request to Lenta!')
            with open('lenta.xml', 'wb') as file:
                file.write(response.content)
        except Exception as e:
            print(e)
            logging.error(e)
            time.sleep(60 * 60)
            continue

        tree = ET.parse('lenta.xml')  # Parse the XML file
        root = tree.getroot()  # Get the root of the XML tree

        # Parse
        for ind, item in enumerate(root.iter('item'), start=1):
            title = item.find('title').text
            print(ind, '-', title)

            try:
                category = item.find('category').text
                if category not in ('Путешествия', 'Спорт'):
                    for element in item:
                        if element.tag == 'link':
                            link = element.text
                        if element.tag in ('author', 'category', 'guid'):
                            item.remove(element)
                        if element.tag == 'description' and len(element.text) < 10:
                            element.text = parse_text(link)  # Parse and update description if condition is met
                tree.write('output.xml', encoding='utf-8')  # Write the updated XML tree to a new file
            except Exception as e:
                logging.error(e, title)
                continue

        print('RSS parsed successfully!')
        time.sleep(60 * 60)  # Sleep for an hour before parsing next iteration


thread = Thread(target=parse_lenta_rss)
thread.start()

app = Flask(__name__)


@app.route('/')
def hello_world() -> str:
    """
    A function that returns a message based on whether a thread is alive.
    """
    message = '&#128994;' if thread.is_alive() else '&#128308;'
    return message


@app.route('/rss')
def index():
    with open('output.xml', 'r', encoding='utf-8') as f:
        rss = f.readlines()
    return ''.join(rss)  # rss


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
