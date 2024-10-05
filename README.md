# Google Maps Business Scraper API

This project is a FastAPI-based Google Maps Business Scraper that allows you to search for business information (such as name, address, website, and phone number) within a specified location. It ensures that the results are accurate by filtering out businesses outside of the specified location. The API is ready to be deployed on platforms like Render.com, Google Cloud Platform (GCP), or AWS.

### Best Google map scraper for accuracy and it actually finds places to scrape unlike other ones which often can't find places and what it doesn’t return the actual places that are there when you actually use Google Maps.

## Main Features 🚀
- **Accurate Results**: Scrapes only the places in your specified location and filters out unwanted results.
- **Fast & Efficient**: Handles pagination and multiple results with speed.
- **Ready for Deployment**: Can be easily deployed on platforms like **Render.com**, **Google Cloud Platform (GCP)**, or **AWS**.
- **Error Handling**: Robust against navigation issues and ensures data extraction even in challenging scenarios.


### How to Use 💡

1. **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/google-maps-scraper-api.git
    cd google-maps-scraper-api
    ```

2. **Set up environment variables**:
    - Create a `.env` file and add your API key:
      ```
      API_KEY=your_api_key
      ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the API**:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8080
    ```

### API Endpoints

#### `POST /search`
**Request**:
```json
{
  "business_type": "restaurant",
  "location": "New York, USA"
}
  ```
**Response:**
```json
[
  {
    "company_name": "Example Business",
    "address": "123 Main St, New York, NY",
    "website": "https://example.com",
    "company_phone": "+1-555-555-5555"
  }
]
```
#### Limitation ⚠️
For cities with populations over 70,000, break the location into suburbs to avoid missing places.
#### Deployment 🌍
This scraper can be easily deployed to Render.com, GCP, or AWS:
```bash
Docker: The provided Dockerfile ensures all dependencies are included, making deployment quick and hassle-free.
docker build -t google-maps-scraper-api .
docker run -p 8080:8080 google-maps-scraper-api
```
Enjoy scraping! 🎉
