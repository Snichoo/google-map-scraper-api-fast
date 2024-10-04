# placesCrawlerV2.py
from playwright.sync_api import sync_playwright
from urllib.parse import unquote
import json

def search(location, business_type):
    query = f"{business_type} in {location}"
    result = []
    PAGINATION = 0

    print(f"Starting search for query: {query}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        while True:
            page = context.new_page()
            url = 'https://www.google.com/localservices/prolist?hl=en&ssta=1&q=' + query + '&oq=' + query + '&src=2&lci=' + str(PAGINATION)
            print(f"Fetching URL: {url} with pagination: {PAGINATION}")
            
            try:
                page.goto(url, timeout=30000)
                page.wait_for_timeout(5000)  # Wait for the page to load
            except Exception as e:
                print(f"Error navigating to URL: {e}")
                break  # Exit the loop if navigation fails

            # Extract the data script
            try:
                data_script = page.eval_on_selector('#yDmH0d > script:nth-child(12)', 'element => element.textContent')
                print("Data script extracted")
            except Exception as e:
                print(f"Error extracting data script: {e}")
                break
            
            try:
                data_script = data_script.replace("AF_initDataCallback(", "").replace("'", "").replace("\n", "")[:-2]
                data_script = data_script.replace("{key:", "{\"key\":").replace(", hash:", ", \"hash\":").replace(", data:", ", \"data\":").replace(", sideChannel:", ", \"sideChannel\":")
                data_script = data_script.replace("\"key\": ds:", "\"key\": \"ds: ").replace(", \"hash\":", "\",\"hash\":")
                data_script = json.loads(data_script)
                print("Data script successfully processed and loaded into JSON")
            except Exception as e:
                print(f"Error processing data script: {e}")
                break

            placesData = data_script["data"][1][0]
            print(f"Places data found: {len(placesData)} records")

            if not placesData:
                print("No more places data found, stopping pagination")
                break  # Exit the loop if no data is found

            try:
                for i in range(len(placesData)):
                    obj = {
                        "company_name": placesData[i][10][5][1],
                        "address": "",
                        "website": "",
                        "company_phone": ""
                    }

                    try:
                        obj["company_phone"] = placesData[i][10][0][0][1][0][0]
                    except TypeError:
                        print(f"Phone number data missing for record {i}")

                    try:
                        obj["website"] = placesData[i][10][1][0]
                    except TypeError:
                        print(f"Website data missing for record {i}")

                    try:
                        obj["address"] = unquote(placesData[i][10][8][0][2]).split("&daddr=")[1].replace("+", " ")
                    except:
                        print(f"Address data missing or malformed for record {i}")

                    # Filter out companies whose address does not include the location
                    if location.lower() in obj["address"].lower():
                        result.append(obj)
                        print(f"Record {i} processed successfully")
                    else:
                        print(f"Record {i} address does not contain location '{location}', skipping")

            except TypeError as e:
                print(f"Error processing placesData: {e}")
                break  # Exit the loop if data processing fails

            if len(placesData) < 20:
                print("Less than 20 records found, stopping pagination")
                break  # Exit the loop if fewer than 20 records are found
            else:
                PAGINATION += len(placesData)
                print(f"Proceeding to next page of results with pagination: {PAGINATION}")

        browser.close()
        print("Browser closed")
    
    print(f"Search completed with {len(result)} results")
    return result
