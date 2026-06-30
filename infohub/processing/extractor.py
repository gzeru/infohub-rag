from bs4 import BeautifulSoup


def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")

    return soup.get_text(separator=" ", strip=True)