import requests
import tldextract

def scrape_leads(query, num_results=10, api_key=None):
    """Scrape leads from Google using SerpAPI"""
    if not api_key:
        return []  # No key provided → no scraping

    url = "https://serpapi.com/search.json"

    params = {
        "q": query,
        "engine": "google",
        "num": num_results,
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
    except Exception as e:
        print("Error fetching SerpAPI results:", e)
        return []

    leads = []
    for result in data.get("organic_results", []):
        title = result.get("title", "")
        link = result.get("link", "")
        domain = tldextract.extract(link).registered_domain
        snippet = result.get("snippet", "")

        leads.append({
            "Business": title,
            "Website": link,
            "Domain": domain,
            "Description": snippet
        })

    return leads
