import time
from threading import Thread

from flask import Flask
from newspaper import Article
import requests
import xml.etree.ElementTree as ET


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
    text = article.text.split('\n')  # Split text into lines
    text = '\n'.join(s for s in text[1:] if s)  # Join non-empty lines with newline
    return text


def parse_lenta_rss():
    while True:
        url = 'https://lenta.ru/rss'
        response = requests.get(url)
        with open('lenta.xml', 'wb') as file:
            file.write(response.content)

        tree = ET.parse('lenta.xml')
        root = tree.getroot()

        for item in root.iter('item'):
            category = item.find('category').text
            if category in ('Путешествия', 'Спорт'):
                continue
            else:
                for element in item:
                    if element.tag == 'link':
                        link = element.text
                    if element.tag in ('author', 'category', 'guid'):
                        item.remove(element)
                    if element.tag == 'description' and len(element.text) < 10:
                        element.text = parse_text(link)
            tree.write('output.xml', encoding='utf-8')
        print('RSS parsed successfully!')
        time.sleep(60 * 60)


thread = Thread(target=parse_lenta_rss)
thread.start()

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/rss')
def index():
    with open('output.xml', 'r', encoding='utf-8') as f:
        rss = f.readlines()
    return ''.join(rss)  # rss


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
