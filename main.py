"""Extract info about the "Cozinhas do Mundo" events from the Portuguese Ticketline.

TODO:
- Make the httpx calls async to speed up retrieving pages
- Add some kind of storage to know when "unseen" events pop up
"""

from dataclasses import dataclass
from typing import Optional, Self
import httpx
from bs4 import BeautifulSoup
import re

import smtplib, ssl, os
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE_URL = "https://ticketline.sapo.pt"

DATE_REGEX = re.compile(r"(202\d)-(\d+)-(\d+)T(\d+):(\d+)")
"""Regex to parse Ticketline's date format — YYYY-MM-DDThh:mm"""

query = "cozinhas do mundo"


@dataclass
class Session:
    date: str
    price: str
    url: Optional[str]

    @staticmethod
    def from_html(html) -> Self:
        return Session(
            date=html.find(class_="date")["content"].replace("T", " "),
            price=html.find(itemprop="lowPrice").text,
            url=html.a.get("href"),
        )

    def to_plaintext(self) -> str:
        return f"- [{" " if self.url else "X"}] [{self.date}] {self.price}"

    def to_html(self) -> str:
        checked = '' if self.url else 'checked="checked"'
        buy = f"<a href={self.url}>Comprar</a>" if self.url else ""
        return f"""<p>
            <input type="checkbox" disabled="disabled" {checked}/>
            {self.date} {self.price} {buy}
        </p>"""

@dataclass
class Event:
    name: str
    url: str

    sessions: list[Session]

    @staticmethod
    def from_html(html) -> Self:
        url = BASE_URL + html.a["href"]
        return Event(
            name=html.a.find(class_="title").text,
            url=url,
            sessions=Event._get_sessions(url),
        )

    @staticmethod
    def _get_sessions(url) -> list[Session]:
        event_page = httpx.get(url)
        parser = BeautifulSoup(event_page, "html.parser")

        sessions_html = parser.find(class_="available_sessions").find_all(
            itemtype="http://schema.org/Event"
        )

        return [Session.from_html(html) for html in sessions_html]

    def to_plaintext(self) -> str:
        sessions = "\n".join(map(Session.to_plaintext, self.sessions))
        return f"### {self.name} — {self.url}\n\n{sessions}\n"

    def to_html(self) -> str:
        return f"""
            <h3><a href="{self.url}">{self.name}</a></h3>
            {"".join(map(Session.to_html, self.sessions))}
        """


def scrape_query_results(query: str) -> list[Event]:
    page = httpx.get(f"{BASE_URL}/pesquisa?query={query}")
    parser = BeautifulSoup(page.text, "html.parser")
    events = parser.find(class_="search_results").find_all(
        itemtype="http://schema.org/Event"
    )
    return [Event.from_html(html) for html in events]

def send_html_email(html: str):
    port = 465
    email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    message = MIMEMultipart("alternative")
    message["Subject"] = f"TimeOut Summary for {date.today()}"
    message["From"] = email
    message["To"] = email
    message.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(email, password)
        server.send_message(message)

if __name__ == "__main__":
    events = scrape_query_results(query)
    html = f"""
    <html>
        <body>
            {"".join(event.to_html() for event in events)}
        </body>
    </html>
    """

    send_html_email(html)
