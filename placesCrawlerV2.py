# placesCrawlerV2.py
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import unquote, quote_plus
import json
import os
import random

# Singleton variables for the browser instance
playwright = None
browser = None

async def get_browser():
    global playwright, browser
    if browser is None:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
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

async def create_stealth_context(browser):
    """Create a browser context with stealth settings to avoid detection"""
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/New_York',
        geolocation={'latitude': 40.7128, 'longitude': -74.0060},
        permissions=['geolocation']
    )
    
    # Add stealth scripts to avoid detection
    await context.add_init_script("""
        // Pass webdriver check
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Pass chrome check
        window.chrome = {
            runtime: {}
        };
        
        // Pass permissions check
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Pass plugins check
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Pass languages check
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    """)
    
    return context

async def search(business_type, location, lead_count=None):
    result = []
    query = f"{business_type} in {location}"

    print(f"Starting search for query: {query}")

    # Extract the suburb/city name from the location for filtering
    # Handle various location formats
    location_parts = location.lower().replace(', australia', '').replace(', usa', '').replace(', uk', '').strip()
    suburb_city = location_parts.split(',')[0].strip()
    print(f"Extracted suburb/city for filtering: {suburb_city}")

    retry_attempts = 3
    attempt = 0

    while attempt < retry_attempts:
        attempt += 1
        try:
            async with context_semaphore:
                browser = await get_browser()
                context = await create_stealth_context(browser)
                try:
                    result = await perform_search(context, business_type, location, suburb_city, lead_count)
                finally:
                    await context.close()
            break
        except Exception as e:
            print(f"Error during search attempt {attempt}: {e}")
            if attempt < retry_attempts:
                print(f"Retrying search (attempt {attempt + 1} of {retry_attempts})...")
                await asyncio.sleep(2 + random.random() * 2)
            else:
                print("Max retries reached. Search failed.")
                return []

    print(f"Search completed with {len(result)} results")
    return result

async def get_local_services_link(page, business_type):
    """
    Search Google and extract the Local Services 'See more' link
    Returns the prolist URL with valid tokens, or None if not found
    """
    
    # Try multiple selectors to find the "More [business]" link
    selectors = [
        # "More plumbers" / "More electricians" etc link
        f'a[href*="/localservices/prolist"]',
        'div[data-hveid] a[href*="localservices"]',
        '[data-async-trigger="reviewDialog"] ~ a',
        'g-more-link a[href*="localservices"]',
    ]
    
    for selector in selectors:
        try:
            link_element = await page.query_selector(selector)
            if link_element:
                href = await link_element.get_attribute('href')
                if href and 'localservices/prolist' in href:
                    # Make sure it's a full URL
                    if href.startswith('/'):
                        href = f'https://www.google.com{href}'
                    print(f"Found Local Services link: {href[:100]}...")
                    return href
        except Exception as e:
            print(f"Error checking selector {selector}: {e}")
            continue
    
    # Alternative: Look for any link containing localservices/prolist in the page
    try:
        all_links = await page.query_selector_all('a[href*="localservices"]')
        for link in all_links:
            href = await link.get_attribute('href')
            if href and 'prolist' in href:
                if href.startswith('/'):
                    href = f'https://www.google.com{href}'
                print(f"Found Local Services link (fallback): {href[:100]}...")
                return href
    except Exception as e:
        print(f"Error in fallback link search: {e}")
    
    return None

async def perform_search(context, business_type, location, suburb_city, lead_count=None):
    result = []
    total_leads_collected = 0
    
    page = await context.new_page()
    
    try:
        # STEP 1: Go to Google Search first
        query = f"{business_type} in {location}"
        encoded_query = quote_plus(query)
        google_search_url = f'https://www.google.com/search?q={encoded_query}&gl=us&hl=en'
        
        print(f"Step 1: Searching Google for: {query}")
        
        # Add random delay to appear more human
        await asyncio.sleep(random.random() * 2 + 1)
        
        await page.goto(google_search_url, timeout=30000, wait_until='networkidle')
        
        # Wait a bit for dynamic content to load
        await asyncio.sleep(2 + random.random())
        
        # STEP 2: Find the "More [service]" link to Local Services
        print("Step 2: Looking for Local Services link...")
        
        local_services_url = await get_local_services_link(page, business_type)
        
        if not local_services_url:
            print("Could not find Local Services link in search results")
            print("Trying alternative approach: clicking on Local Services section...")
            
            # Try clicking on the Local Services section if it exists
            try:
                # Look for "More X nearby" or similar text
                more_link = await page.query_selector('text=/More .* nearby/i')
                if more_link:
                    await more_link.click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)
                    
                    # Check if we're now on the prolist page
                    if 'localservices/prolist' in page.url:
                        local_services_url = page.url
                        print(f"Successfully navigated to Local Services via click")
            except Exception as e:
                print(f"Alternative approach failed: {e}")
        
        if not local_services_url:
            # Last resort: try direct URL with different parameters
            print("Trying direct navigation as last resort...")
            direct_url = f'https://www.google.com/localservices/prolist?src=1&q={encoded_query}&hl=en&gl=us'
            await page.goto(direct_url, timeout=30000)
            await asyncio.sleep(2)
            
            # Check if we got results
            content = await page.content()
            if 'Try using different filters' in content:
                print("Direct navigation also failed - no results available")
                await page.close()
                return result
            else:
                local_services_url = page.url
        
        # STEP 3: Navigate to Local Services page and scrape
        if local_services_url and local_services_url != page.url:
            print(f"Step 3: Navigating to Local Services page...")
            await asyncio.sleep(random.random() + 1)
            await page.goto(local_services_url, timeout=30000, wait_until='networkidle')
            await asyncio.sleep(2)
        
        # Now scrape the results with pagination
        PAGINATION = 0
        max_pages = 10  # Safety limit
        pages_scraped = 0
        
        while pages_scraped < max_pages:
            pages_scraped += 1
            print(f"Scraping page {pages_scraped}...")
            
            # Extract data from the current page
            page_results = await extract_page_data(page, suburb_city)
            
            if not page_results:
                print("No more results found")
                break
            
            for item in page_results:
                result.append(item)
                total_leads_collected += 1
                
                if lead_count and total_leads_collected >= lead_count:
                    print(f"Lead count limit ({lead_count}) reached")
                    await page.close()
                    return result
            
            print(f"Collected {len(page_results)} leads from this page. Total: {total_leads_collected}")
            
            # Check for "Show more" / pagination
            has_more = await try_load_more_results(page)
            if not has_more:
                print("No more pages available")
                break
            
            await asyncio.sleep(1 + random.random())
        
    except Exception as e:
        print(f"Error in perform_search: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        await page.close()
    
    return result

async def extract_page_data(page, suburb_city):
    """Extract business data from the current Local Services page"""
    results = []
    
    try:
        # Method 1: Try to extract from the script tag (original method)
        try:
            scripts = await page.query_selector_all('script')
            for script in scripts:
                content = await script.text_content()
                if content and 'AF_initDataCallback' in content:
                    data = parse_af_data(content)
                    if data:
                        for item in data:
                            if not suburb_city or suburb_city in item.get('address', '').lower():
                                results.append(item)
                            else:
                                print(f"Filtered out: {item.get('company_name', 'Unknown')} - address mismatch")
                        if results:
                            return results
        except Exception as e:
            print(f"Script extraction method failed: {e}")
        
        # Method 2: Extract directly from DOM elements
        print("Trying DOM extraction method...")
        
        # Wait for business cards to load
        await page.wait_for_selector('[data-profile-url-path], [data-ved] .rllt__details, .xYjf2e', timeout=10000)
        
        # Try different selectors for business cards
        card_selectors = [
            '[data-profile-url-path]',  # New format
            '.rllt__details',            # Older format
            '.xYjf2e',                   # Alternative format
            '[jscontroller] [data-ved]'  # Generic format
        ]
        
        for selector in card_selectors:
            cards = await page.query_selector_all(selector)
            if cards and len(cards) > 0:
                print(f"Found {len(cards)} business cards with selector: {selector}")
                
                for card in cards:
                    try:
                        item = await extract_card_data(card, page)
                        if item and item.get('company_name'):
                            if not suburb_city or suburb_city in item.get('address', '').lower():
                                results.append(item)
                            else:
                                print(f"Filtered out: {item.get('company_name', 'Unknown')} - address mismatch")
                    except Exception as e:
                        print(f"Error extracting card data: {e}")
                        continue
                
                if results:
                    break
        
    except Exception as e:
        print(f"Error in extract_page_data: {e}")
        import traceback
        traceback.print_exc()
    
    return results

async def extract_card_data(card, page):
    """Extract data from a single business card element"""
    item = {
        'company_name': '',
        'address': '',
        'website': '',
        'company_phone': ''
    }
    
    try:
        # Try multiple selectors for company name
        name_selectors = [
            '[data-company-name]',
            '.xYjf2e',
            '.rgnuSb',
            '[role="heading"]',
            'div[class*="title"]',
            'span[class*="name"]'
        ]
        
        for sel in name_selectors:
            try:
                name_el = await card.query_selector(sel)
                if name_el:
                    name = await name_el.text_content()
                    if name and len(name.strip()) > 1:
                        item['company_name'] = name.strip()
                        break
            except:
                continue
        
        # If still no name, try getting text content of the card itself
        if not item['company_name']:
            text = await card.text_content()
            if text:
                # Usually the first line is the company name
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if lines:
                    item['company_name'] = lines[0][:100]  # Limit length
        
        # Try to get phone number
        phone_pattern = await card.query_selector('[data-phone-number], a[href^="tel:"]')
        if phone_pattern:
            phone = await phone_pattern.get_attribute('data-phone-number') or await phone_pattern.get_attribute('href')
            if phone:
                item['company_phone'] = phone.replace('tel:', '').strip()
        
        # Try to get address
        address_el = await card.query_selector('[data-address], .rllt__wrapped')
        if address_el:
            item['address'] = (await address_el.text_content() or '').strip()
        
        # Try to get website from data attribute or link
        website_el = await card.query_selector('a[data-website], a[href*="http"]:not([href*="google"])')
        if website_el:
            item['website'] = await website_el.get_attribute('href') or ''
        
    except Exception as e:
        print(f"Error extracting card data: {e}")
    
    return item

def parse_af_data(script_content):
    """Parse the AF_initDataCallback script content to extract business data"""
    results = []
    
    try:
        # Clean up the script content
        data_script = script_content.replace("AF_initDataCallback(", "").replace("'", "").replace("\n", "")
        if data_script.endswith(");"):
            data_script = data_script[:-2]
        elif data_script.endswith(")"):
            data_script = data_script[:-1]
        
        # Try to fix JSON formatting
        data_script = data_script.replace("{key:", '{"key":')
        data_script = data_script.replace(", hash:", ', "hash":')
        data_script = data_script.replace(", data:", ', "data":')
        data_script = data_script.replace(", sideChannel:", ', "sideChannel":')
        data_script = data_script.replace('"key": ds:', '"key": "ds:')
        data_script = data_script.replace(', "hash":', '", "hash":')
        
        data = json.loads(data_script)
        
        if "data" in data and len(data["data"]) > 1 and data["data"][1]:
            places_data = data["data"][1][0] if data["data"][1] else []
            
            for place in places_data:
                try:
                    company_name = ""
                    address = ""
                    website = ""
                    company_phone = ""
                    
                    try:
                        company_name = place[10][5][1]
                    except:
                        pass
                    
                    try:
                        address_raw = place[10][8][0][2]
                        address = unquote(address_raw).split("&daddr=")[1].replace("+", " ")
                    except:
                        pass
                    
                    try:
                        website = place[10][1][0]
                    except:
                        pass
                    
                    try:
                        company_phone = place[10][0][0][1][1][0]
                    except:
                        pass
                    
                    if company_name:
                        results.append({
                            "company_name": company_name,
                            "address": address,
                            "website": website,
                            "company_phone": company_phone
                        })
                except Exception as e:
                    continue
                    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
    except Exception as e:
        print(f"Error parsing AF data: {e}")
    
    return results

async def try_load_more_results(page):
    """Try to load more results by clicking 'Show more' or scrolling"""
    
    try:
        # Look for "Show more" button
        show_more_selectors = [
            'button:has-text("Show more")',
            'button:has-text("More results")',
            '[aria-label*="more results"]',
            '.show-more-button',
            'text=/Show more/i'
        ]
        
        for selector in show_more_selectors:
            try:
                button = await page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        await button.click()
                        await asyncio.sleep(2)
                        return True
            except:
                continue
        
        # Try scrolling to load more
        scroll_height_before = await page.evaluate('document.body.scrollHeight')
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(2)
        scroll_height_after = await page.evaluate('document.body.scrollHeight')
        
        if scroll_height_after > scroll_height_before:
            return True
        
    except Exception as e:
        print(f"Error trying to load more results: {e}")
    
    return False