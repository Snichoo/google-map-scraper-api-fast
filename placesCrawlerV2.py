# placesCrawlerV2.py
from playwright.sync_api import sync_playwright
from urllib.parse import unquote
import json

def search(business_type, location):
    result = []
    PAGINATION = 0
    query = f"{business_type} in {location}"

    print(f"Starting search for query: {query}")

    # Extract the suburb/city name from the location (remove ', Australia')
    suburb_city = location.replace(', Australia', '').strip().lower()
    print(f"Extracted suburb/city for filtering: {suburb_city}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        while True:
            page = context.new_page()
            url = 'https://www.google.com/localservices/prolist?hl=en&ssta=1&q='+query+'&oq='+query+'&src=2&lci='+str(PAGINATION)
            
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
                # Print the entire data_script for inspection
                print(f"Data script content: {data_script}")

                # Update how you access 'placesData' based on the new structure
                try:
                    placesData = data_script_json["data"][1][0]
                except (KeyError, IndexError, TypeError) as e:
                    print(f"Failed to extract 'placesData': {e}")
                    break  # Or handle the error appropriately

                # After extracting data_script
                if not data_script:
                    print("Data script is empty or None")
                    break  # Exit the loop or handle accordingly

                # When parsing data_script
                try:
                    data_script_json = json.loads(data_script)
                except json.JSONDecodeError as e:
                    print(f"JSON decoding failed: {e}")
                    break
                print("Data script extracted")
            except Exception as e:
                print(f"Error extracting data script: {e}")
                break
            
            try:
                data_script = data_script.replace("AF_initDataCallback(","").replace("'","").replace("\n","")[:-2]
                data_script = data_script.replace("{key:","{\"key\":").replace(", hash:",", \"hash\":").replace(", data:",", \"data\":").replace(", sideChannel:",", \"sideChannel\":")
                data_script = data_script.replace("\"key\": ds:","\"key\": \"ds: ").replace(", \"hash\":","\",\"hash\":")
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
                    # Extract required fields
                    try:
                        company_name = placesData[i][10][5][1]
                    except:
                        company_name = ""

                    try:
                        address_raw = placesData[i][10][8][0][2]
                        address = unquote(address_raw).split("&daddr=")[1].replace("+"," ")
                    except:
                        address = ""

                    try:
                        website = placesData[i][10][1][0]
                    except:
                        website = ""

                    try:
                        company_phone = placesData[i][10][0][0][1][1][0]
                    except:
                        company_phone = ""

                    # Filter out companies whose address does not include the suburb/city name
                    if suburb_city in address.lower():
                        obj = {
                            "company_name": company_name,
                            "address": address,
                            "website": website,
                            "company_phone": company_phone
                        }
                        result.append(obj)
                        print(f"Record {i} processed and added to results")
                    else:
                        print(f"Record {i} excluded due to address mismatch")

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
