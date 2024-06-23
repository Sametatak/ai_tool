import openai
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

logging.basicConfig(filename='main_task_debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

openai.api_key = os.getenv("OPENAI_API_KEY")

product_categories = {
    "Cooking_Appliances": ["Freestanding Oven", "Built-In Oven", "Cooktop", "Cooking Range"],
    "Cooling_Freezing": ["Refrigerator", "Freezer", "Bottle Cooler"],
    "Washing_Machine": ["Washing_Machine"],
    "Dishwasher": ["Dishwasher"],
    "Dryer": ["Dryer"],
    "Television": ["Television"]
}

information_categories = {
    "Event": ["Exhibition/Fair", "Convention/Summit", "Conference", "Corporate Meeting", "Opening", "Webinar", "Workshop", "Networking", "Charity"],
    "Product": ["New Product", "New Feature/Specification", "New Technology", "Product Change", "Product Discontinue"],
    "Market": ["Competitor", "Consumer Trend", "Market Indicator", "Price Increase", "Price Decrease", "Promotion", "Mergers and Acquisitions", "Investment", "Bankrupt", "Public Offering"],
    "Economy": ["Raw Material Price Change", "Energy Price Change", "Unemployment", "Employment", "Interest Rate Change", "Economic Growth", "Recession", "Inflation", "Currency Fluctuation"],
    "Public": ["Legislative Change", "Regulation Change", "Incentive grant", "Tender"]
}

def search_perplexica(query):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get("http://localhost:3000")

        wait = WebDriverWait(driver, 20)
        search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Ask anything...']")))

        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        time.sleep(20)  
        
        results = driver.find_elements(By.CSS_SELECTOR, "a")
        
        websites = []
        for result in results:
            url = result.get_attribute('href')
            if url and not url.startswith("http://localhost"):
                websites.append(url)
                if len(websites) >= 20:  
                    break
        
        if not websites:
            logging.warning(f"No external URLs found for query '{query}'")
        
        return websites
    except Exception as e:
        logging.error(f"An error occurred during Perplexica search for '{query}': {e}")
        return []
    finally:
        driver.quit()

def get_best_sources_with_perplexica(query):
    try:
        search_results = search_perplexica(query)
        if search_results:
            logging.debug(f"Perplexica results for query '{query}': {search_results}")
        else:
            logging.warning(f"No results found for query '{query}'")
        return search_results
    except Exception as e:
        logging.error(f"Error during Perplexica search for query '{query}': {e}")
        return []

def scrape_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)  
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        content = "\n".join([para.get_text() for para in paragraphs])
        return content
    except requests.exceptions.Timeout:
        logging.error(f"Timeout occurred for URL {url}")
        return "Timeout occurred while retrieving content"
    except requests.exceptions.RequestException as e:
        logging.error(f"Error: {e} for URL {url}")
        return "Error retrieving content"
    except Exception as e:
        logging.error(f"Unexpected error: {e} for URL {url}")
        return "Unexpected error retrieving content"

url_list = []

for category, subcategories in product_categories.items():
    for subcategory in subcategories:
        query = f"Find URLs for {subcategory}"  
        logging.debug(f"Processing query: {query}")
        sources = get_best_sources_with_perplexica(query)
        if not sources:
            logging.warning(f"No sources found for query: {query}")
            continue
        for source in sources:
            url_list.append({"Product Category": category, "Product Subcategory": subcategory, "Source": source})

if url_list:
    df = pd.DataFrame(url_list)
    df.to_csv('best_sources.csv', index=False)
    logging.info("Sources identified and saved to best_sources.csv")
else:
    logging.warning("No sources to save. Check the API response and URL extraction process.")

output_dir = "scraped_content"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for entry in url_list:
    category = entry['Product Category']
    subcategory = entry['Product Subcategory']
    source = entry['Source']
    logging.debug(f"Scraping content from {source}")
    content = scrape_content(source)
    logging.debug(f"Content from {source}: {content[:200]}")  
    if content:
        filename = os.path.join(output_dir, f'{category}_{subcategory.replace(" ", "_")}_content.txt').replace('/', '_')
        with open(filename, 'a', encoding='utf-8') as f:  
            f.write(content + "\n\n")

logging.info("Content scraped and saved to text files")

def process_relevant_information(product_category, product_subcategory, content):
    prompt = f"Extract relevant information for the following categories and subcategories for the product '{product_subcategory}' in '{product_category.replace('_', ' ')}':\n\n"
    for main_category, subcategories in information_categories.items():
        prompt += f"{main_category}:\n"
        for subcategory in subcategories:
            prompt += f"  - {subcategory}\n"
    prompt += f"\nContent:\n{content}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000  
        )
        relevant_info = response.choices[0]['message']['content'].strip()
        return relevant_info
    except Exception as e:
        logging.error(f"Error during processing content for product '{product_subcategory}' in category '{product_category}': {e}")
        return "Error processing content"

for category, subcategories in product_categories.items():
    for subcategory in subcategories:
        filename = os.path.join(output_dir, f'{category}_{subcategory.replace(" ", "_")}_content.txt').replace('/', '_')
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            relevant_info = process_relevant_information(category, subcategory, content)
            relevant_filename = os.path.join(output_dir, f'{category}_{subcategory.replace(" ", "_")}_relevant_info.txt').replace('/', '_')
            with open(relevant_filename, 'w', encoding='utf-8') as f:
                f.write(relevant_info)

logging.info("Relevant information processed and saved to text files")
