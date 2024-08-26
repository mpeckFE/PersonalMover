import requests
import time
import sys
import getopt
from datetime import datetime, timedelta, timezone

# Configuration
API_TOKEN = 'ykmBC6ydrNqnQtervht0l0Q4J2DotvQU:c2nAc4VZYt0nlmIPYGU26vipOYegKfgS'
BASE_URL = 'https://fewiki.forward-edge.net/api'
HEADERS = {'Authorization': f'Token {API_TOKEN}'}
BOOKSTACK_BASE_URL = 'https://fewiki.forward-edge.net/books'

def get_books(shelf_id):
    """Fetches books from a specific shelf directly using its API"""
    url = f"{BASE_URL}/shelves/{shelf_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()['books']

def get_articles(book_id):
    """Fetches articles (pages and chapters) from a specific book using its API"""
    url = f"{BASE_URL}/books/{book_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()['contents']

def get_chapter_contents(chapter_id):
    """Fetches pages from a specific chapter using its API"""
    url = f"{BASE_URL}/chapters/{chapter_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()['pages']

def is_within_last_day(date_str):
    """Checks if the given date string is within the last day"""
    article_date = datetime.fromisoformat(date_str)
    if article_date.tzinfo is None:
        article_date = article_date.replace(tzinfo=timezone.utc)
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    return article_date > one_day_ago

def send_slack_message(message):
    """Uses the slack webhook to send a message in the correct chat"""
    payload = '{"text":"%s"}' % message
    response = requests.post("https://hooks.slack.com/services/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", 
                             data=payload)
    print(response.text)

def construct_page_url(book_slug, page_slug):
    """Constructs the URL of a page using the book slug and page slug"""
    return f"{BOOKSTACK_BASE_URL}/{book_slug}/page/{page_slug}"

def main(argv):
    shelf_id = 1  # Using the known ID of the "Engineering" shelf
    books = get_books(shelf_id)

    final_message = []
    
    for book in books:
        book_id = book['id']
        book_name = book['name']
        contents = get_articles(book_id)
        article_messages = []
        
        for content in contents:
            if content['type'] == 'page':  # Handle pages directly in the book
                created_at = content['created_at']
                if is_within_last_day(created_at):
                    article_url = content['url']
                    article_message = f"> -*Article Name*: <{article_url}|{content['name']}>"
                    article_messages.append(article_message)
                    print(f"Book Name: {book_name}, Article Name: {content['name']}, Created On: {created_at}, URL: {article_url}")
            elif content['type'] == 'chapter':  # Handle chapters by retrieving pages within them
                chapter_id = content['id']
                chapter_pages = get_chapter_contents(chapter_id)
                for page in chapter_pages:
                    created_at = page['created_at']
                    if is_within_last_day(created_at):
                        page_url = construct_page_url(page['book_slug'], page['slug'])
                        article_message = f"> -*Page in Chapter {content['name']}*: <{page_url}|{page['name']}>"
                        article_messages.append(article_message)
                        print(f"Book Name: {book_name}, Chapter Name: {content['name']}, Page Name: {page['name']}, Created On: {created_at}, URL: {page_url}")
            time.sleep(0.1)  # To avoid hitting rate limits
        
        if article_messages:
            book_message = f"The following is a list of all pages that were created in the book _*{book_name}*_:\n" + "\n".join(article_messages)
            final_message.append(book_message)

    if not final_message:
        final_message.append("No articles were created in any books in the last day.")

    message = "\n\n".join(final_message)

    try: 
        opts, args = getopt.getopt(argv, "hm:", ["message="])
    except getopt.GetoptError:
        print('SlackMessage.py -m <message>')
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            print ('SlackMessage.py -m <message>')
            sys.exit()
        elif opt in ("-m", "--message"):
            message = arg
    
    send_slack_message(message)

if __name__ == "__main__":
    main(sys.argv[1:])
