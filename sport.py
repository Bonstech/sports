from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import uuid
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, static_folder='templates')

# Dictionary to store the mapping between article IDs and their URLs
article_url_map = {}
scraped_articles = []

def scrape_articles():
    """Function to scrape articles from the website."""
    global scraped_articles
    url = 'https://www.ghanaweb.com/GhanaHomePage/SportsArchive/'  # The URL to scrape
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        soup = BeautifulSoup(response.content, 'lxml')

        # Extract the main container that holds the articles
        articles = []
        main_container = soup.find('ul', class_='inner-lead-story-bottom')  # Update the class name based on the structure

        if main_container:
            # Find all the nested divs or elements containing articles
            for news_item in main_container.find_all('li', recursive=True):  # Use recursive search to go deep
                # Check for specific child elements to extract relevant data
                headline_tag = news_item.find('h2') or news_item.find('h3')  # Adjust based on the available structure
                headline = headline_tag.text.strip() if headline_tag else 'No headline available'

                # Extract the link to the article if present
                link_tag = news_item.find('a', href=True)
                article_url = urljoin(url, link_tag['href']) if link_tag else '#'

                # Generate a unique ID for each article
                article_id = str(uuid.uuid4())
                article_url_map[article_id] = article_url  # Store the URL with its unique ID

                # Extract image if available
                img_tag = news_item.find('img')
                img_url = img_tag.get('src') if img_tag else ''
                full_img_url = urljoin(url, img_url)

                # Add the scraped content to the list
                articles.append({
                    'headline': headline,
                    'image': full_img_url,
                    'id': article_id  # Use the unique ID instead of the URL
                })

        # Update the global scraped_articles list
        scraped_articles = articles
        print("Articles scraped successfully.")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

@app.route('/')
def display_articles():
    # Display the scraped articles
    return render_template('sport.html', articles=scraped_articles)

@app.route('/view_article/<article_id>')
def view_article(article_id):
    # Get the article URL from the mapping dictionary using the article ID
    article_url = article_url_map.get(article_id)

    if article_url:
        try:
            response = requests.get(article_url)
            response.raise_for_status()  # Check if the request was successful
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract the main content of the article
            article_content = ''
            content_container = soup.find('div', class_='article-content-area')  # Update based on the actual article structure

            if content_container:
                # Get the full text content of the article
                article_content = content_container.get_text(separator=" ", strip=True)

            # Extract image if available
            img_tag = content_container.find('img') if content_container else None
            img_url = img_tag.get('src') if img_tag else ''
            full_img_url = urljoin(article_url, img_url)

            # Pass the data to the template
            return render_template('sportcont.html', content=article_content, image=full_img_url)

        except requests.exceptions.RequestException as e:
            return f"Error fetching the article: {e}"
    else:
        return "Article not found."

if __name__ == '__main__':
    # Configure APScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=scrape_articles, trigger="interval", minutes=30)  # Scrape every 30 minutes
    scheduler.start()

    # Scrape the articles initially when the app starts
    scrape_articles()

    try:
        app.run(debug=True, port=5003)
    finally:
        # Shut down the scheduler when exiting the app
        scheduler.shutdown()
