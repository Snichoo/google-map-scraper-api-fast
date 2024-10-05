# Google Maps Scraper API 🗺️

This project provides a **fast**, **reliable**, and **accurate** scraper for extracting business data from Google Maps. Unlike many scrapers, it **consistently finds and returns real places** within your specified location without straying beyond the boundaries. 

### Main Features 🚀
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
**Limitation ⚠️**
For cities with populations over 70,000, break the location into suburbs to avoid missing places.
**Deployment 🌍**
This scraper can be easily deployed to Render.com, GCP, or AWS:
```bash
Docker: The provided Dockerfile ensures all dependencies are included, making deployment quick and hassle-free.
docker build -t google-maps-scraper-api .
docker run -p 8080:8080 google-maps-scraper-api
```
Enjoy scraping! 🎉
