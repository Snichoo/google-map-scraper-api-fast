# placesCrawlerV2.py
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import unquote
import json
import os
# Singleton variables for the browser instance
playwright = None
browser = None

async def get_browser():
    global playwright, browser
    if browser is None:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
    return browser

async def close_browser():
    global playwright, browser
    if browser:
        await browser.close()
        browser = None
    if playwright:
        await playwright.stop()
        playwright = None

# Read MAX_CONTEXTS from environment variable or default to 5
MAX_CONTEXTS = int(os.getenv('MAX_CONTEXTS', '5'))
context_semaphore = asyncio.Semaphore(MAX_CONTEXTS)

async def search(business_type, location, lead_count=None):
    result = []
    query = f"{business_type} in {location}"

    print(f"Starting search for query: {query}")

    # Extract the suburb/city name from the location (remove ', Australia')
    suburb_city = location.replace(', Australia', '').strip().lower()
    print(f"Extracted suburb/city for filtering: {suburb_city}")

    retry_attempts = 3  # Number of retry attempts
    attempt = 0

    while attempt < retry_attempts:
        attempt += 1
        try:
            async with context_semaphore:
                browser = await get_browser()
                context = await browser.new_context()
                try:
                    result = await perform_search(context, query, suburb_city, lead_count)
                finally:
                    await context.close()

            # If perform_search completes without raising an exception, break out of retry loop
            break
        except Exception as e:
            print(f"Error during search attempt {attempt}: {e}")
            if attempt < retry_attempts:
                print(f"Retrying search (attempt {attempt + 1} of {retry_attempts})...")
                await asyncio.sleep(2)  # Optional: add a delay before retrying
            else:
                print("Max retries reached. Search failed.")
                # Return empty result or handle as needed
                return []

    print(f"Search completed with {len(result)} results")
    return result

async def perform_search(context, query, suburb_city, lead_count=None):
    result = []
    total_leads_collected = 0
    PAGINATION = 0
    while True:
        page = await context.new_page()
        url = f'https://www.google.com/localservices/prolist?hl=en&ssta=1&q={query}&oq={query}&src=2&lci={PAGINATION}'

        print(f"Fetching URL: {url} with pagination: {PAGINATION}")

        try:
            await page.goto(url, timeout=30000)  # Set timeout explicitly
        except Exception as e:
            print(f"Error navigating to URL: {e}")
            await page.close()
            raise e  # Raise exception to trigger retry

        # Extract the data script
        try:
            data_script = await page.eval_on_selector(
                '#yDmH0d > script:nth-child(12)',
                'element => element.textContent'
            )
            print("Data script extracted")
        except Exception as e:
            print(f"Error extracting data script: {e}")
            await page.close()
            raise e  # Raise exception to trigger retry

        try:
            data_script = data_script.replace("AF_initDataCallback(", "").replace("'", "").replace("\n", "")[:-2]
            data_script = data_script.replace("{key:", "{\"key\":").replace(", hash:", ", \"hash\":").replace(", data:", ", \"data\":").replace(", sideChannel:", ", \"sideChannel\":")
            data_script = data_script.replace("\"key\": ds:", "\"key\": \"ds:").replace(", \"hash\":", "\", \"hash\":")
            data_script = json.loads(data_script)
            print("Data script successfully processed and loaded into JSON")
        except Exception as e:
            print(f"Error processing data script: {e}")
            await page.close()
            raise e  # Raise exception to trigger retry

        try:
            # Check if places data is available
            if "data" in data_script and len(data_script["data"]) > 1 and data_script["data"][1]:
                placesData = data_script["data"][1][0]
                print(f"Places data found: {len(placesData)} records")
            else:
                print("No places data found, stopping pagination")
                await page.close()
                break  # Exit the loop if no data is found
        except (KeyError, IndexError, TypeError) as e:
            print(f"Error accessing places data: {e}")
            await page.close()
            # If no places are found, we don't consider it an error that triggers a retry
            break

        if not placesData:
            print("No more places data found, stopping pagination")
            await page.close()
            break  # Exit the loop if no data is found

        try:
            for i, place in enumerate(placesData):
                # Extract required fields
                try:
                    company_name = place[10][5][1]
                except:
                    company_name = ""

                try:
                    address_raw = place[10][8][0][2]
                    address = unquote(address_raw).split("&daddr=")[1].replace("+", " ")
                except:
                    address = ""

                try:
                    website = place[10][1][0]
                except:
                    website = ""

                try:
                    company_phone = place[10][0][0][1][1][0]
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
                    total_leads_collected += 1

                    if lead_count and total_leads_collected >= lead_count:
                        print("Lead count limit reached, stopping pagination")
                        await page.close()
                        return result  # Exit the function as we've reached the lead count
                else:
                    print(f"Record {i} excluded due to address mismatch")


        except Exception as e:
            print(f"Error processing placesData: {e}")
            await page.close()
            raise e  # Raise exception to trigger retry

        await page.close()

        if lead_count and total_leads_collected >= lead_count:
            print("Lead count limit reached, stopping pagination")
            break  # Break out of the while loop

        # Proceed to next page if lead count not reached
        if len(placesData) < 20:
            print("Less than 20 records found, stopping pagination")
            break  # Exit the loop if fewer than 20 records are found
        else:
            PAGINATION += len(placesData)
            print(f"Proceeding to next page of results with pagination: {PAGINATION}")

    return result
