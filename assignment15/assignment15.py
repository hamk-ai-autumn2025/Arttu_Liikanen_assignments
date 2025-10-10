import os
import asyncio
import threading
from flask import Flask, request, render_template_string
from openai import OpenAI
from pydantic import BaseModel
from crawl4ai import (
    AsyncWebCrawler, BrowserConfig, CrawlerRunConfig,
    DefaultMarkdownGenerator, PruningContentFilter,
    JsonCssExtractionStrategy
)

# ======================================================
# Flask app setup
# ======================================================
app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set your OpenAI API key in environment variable OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ======================================================
# Product Data Model
# ======================================================
class ProductData(BaseModel):
    product_name: str
    price: str
    review_rating: str
    original_description: str

# ======================================================
# HTML template
# ======================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Product Info Extractor</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
<style>
{% raw %}
body { font-family: 'Roboto', Arial, sans-serif; margin: 40px; background: #fafafa; }
form { margin-bottom: 20px; }
input[type="text"] { width: 400px; padding: 8px; }
input[type="submit"] { padding: 8px 16px; margin-left: 8px; }
pre { background: #f5f5f5; padding: 16px; border-radius: 8px; white-space: pre-wrap; }
.error { color: red; }
h2 { margin-top: 30px; }
.improved { background: #e8f4fd; padding: 15px; border-radius: 8px; }
{% endraw %}
</style>
</head>
<body>
<h1>Product Info Extractor</h1>
<form method="POST">
<label for="product_url">Enter Product URL:</label><br>
<input type="text" id="product_url" name="product_url" placeholder="https://www.amazon.com/dp/..." required>
<input type="submit" value="Extract & Rewrite">
</form>

{% if error %}
<p class="error">{{ error }}</p>
{% endif %}

{% if product_data %}
<h2>Product Data (JSON)</h2>
<pre>{{ product_data }}</pre>

<h2>Improved Description</h2>
<div class="improved">{{ improved_description }}</div>
{% endif %}
</body>
</html>
"""

# ======================================================
# Async function to scrape product info
# ======================================================
async def extract_product_info(url):
    browser_config = BrowserConfig(headless=True, verbose=False)
    content_filter = PruningContentFilter(threshold=0.5)
    markdown_generator = DefaultMarkdownGenerator(content_filter=content_filter)
    crawl_config = CrawlerRunConfig(markdown_generator=markdown_generator)

    css_selectors = {
        "product_name": "h1.product-title",
        "price": "span.price",
        "review_rating": "span.review-rating",
        "description": "div.product-description"
    }
    extraction_strategy = JsonCssExtractionStrategy(css_selectors)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result_obj = await crawler.arun(
            url=url,
            config=crawl_config,
            extraction_strategy=extraction_strategy
        )

    try:
        data = result_obj.to_dict()
    except Exception:
        data = {}

    data.setdefault("product_name", "Unknown Product")
    data.setdefault("price", "N/A")
    data.setdefault("review_rating", "N/A")
    data.setdefault("description", "No description found")

    return data

# ======================================================
# Thread-safe loop for async crawling
# ======================================================
crawl_loop = asyncio.new_event_loop()
threading.Thread(target=crawl_loop.run_forever, daemon=True).start()

def run_coro_threadsafe(coro):
    future = asyncio.run_coroutine_threadsafe(coro, crawl_loop)
    return future.result()

# ======================================================
# Function to rewrite description via OpenAI
# ======================================================
def rewrite_description(data):
    prompt = (
        f"Product: {data['product_name']}\n"
        f"Price: {data['price']}\n"
        f"Rating: {data['review_rating']}\n"
        f"Description: {data['description']}\n\n"
        "Rewrite this product description to make it more persuasive and appealing, "
        "considering the price and review rating."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating improved description: {e}"

# ======================================================
# Flask route
# ======================================================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        product_url = request.form.get("product_url")
        if not product_url:
            return render_template_string(
                HTML_TEMPLATE, error="Please enter a product URL.",
                product_data=None, improved_description=None
            )
        try:
            data = run_coro_threadsafe(extract_product_info(product_url))
        except Exception as e:
            return render_template_string(
                HTML_TEMPLATE, error=f"Error scraping product: {e}",
                product_data=None, improved_description=None
            )

        # Convert scraped data to Pydantic model
        product_model = ProductData(
            product_name=data['product_name'],
            price=data['price'],
            review_rating=data['review_rating'],
            original_description=data['description']
        )

        # Serialize with model_dump_json
        json_data = product_model.model_dump_json(indent=2)

        # Improved description separate
        improved_desc = rewrite_description(data)

        return render_template_string(
            HTML_TEMPLATE,
            error=None,
            product_data=json_data,
            improved_description=improved_desc
        )

    return render_template_string(
        HTML_TEMPLATE,
        error=None,
        product_data=None,
        improved_description=None
    )

# ======================================================
# Run the app
# ======================================================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
