import httpx
from bs4 import BeautifulSoup

base_url = "https://ticketline.sapo.pt"
query = "cozinhas do mundo"
page = httpx.get(f"{base_url}/pesquisa?query={query}")

parser = BeautifulSoup(page.text, "html.parser")

event_urls = [
    base_url + event.a["href"]
    for event in parser.find_all(itemtype="http://schema.org/Event")
]

print(event_urls)
