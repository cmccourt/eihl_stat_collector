import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def get_date_format(text: str, fmt: str) -> datetime or None:
    try:
        text_dt = datetime.strptime(text, fmt)
        return text_dt
    except ValueError:
        return None


def extract_float_from_str(value: str):
    float_value = None
    if re.findall(r"(\d+.\d+)(?=%)", value):
        float_value = float(re.search(r"(\d+.\d+)(?=%)", value).group(1))
    else:
        try:
            float_value = float(value)
        except ValueError:
            print(f"Float conversion failed. Value: {value}")
    return float_value


def get_html_content(url: str) -> BeautifulSoup:
    response = requests.get(url)
    res_beaus = BeautifulSoup(response.content, 'html.parser')
    return res_beaus


def get_ignore_words():
    ignore_words = []
    try:
        with open("../../settings/ignore_list.txt", "r") as ign_words_file:
            # Create a list of ignore words for comparison
            # convert word to lowercase and remove any whitespace
            ignore_words = [f"{word.lower().strip()} " for word in ign_words_file]
    except IOError:
        print("Could not find the file")
    return ignore_words


def get_page_text(url: str, ignore_words: list = None) -> str:
    response = requests.get(url)
    res_beaus = BeautifulSoup(response.content, 'html.parser')
    page_words: str = res_beaus.body.get_text()
    html_content = page_words.strip('\t\r\n')
    page_words = re.sub(r'\W', ' ', html_content)

    if ignore_words is None:
        ignore_words = get_ignore_words()
    ignore_reg = '|'.join(ignore_words)
    page_words = re.sub(ignore_reg, "", page_words)

    return page_words