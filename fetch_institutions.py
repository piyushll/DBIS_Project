import requests
import time
import re

# OpenAlex API settings
OPENALEX_HEADERS = {
    "User-Agent": "DBMS_Project/22B2255_22B2217_22B3909_22B2211@email.com"
}

def extract_doi_from_url(url):
    """Extract DOI from a URL if present"""
    if not url:
        return None
        
    # Check for DOI patterns in the URL
    doi_patterns = [
        r'doi\.org/([^/\s]+/[^/\s]+)',  # matches doi.org/10.1234/something
        r'doi:([^/\s]+/[^/\s]+)',       # matches doi:10.1234/something
        r'([0-9]+\.[0-9]+/[^/\s]+)'     # matches 10.1234/something anywhere in URL
    ]
    
    for pattern in doi_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_openalex_data_from_doi(doi):
    """
    Queries OpenAlex API for a given DOI and returns a list of author affiliations with their cities.
    """
    api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    
    try:
        print(f"Fetching data for DOI: {doi}")
        response = requests.get(api_url, headers=OPENALEX_HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch DOI {doi}: {response.status_code}")
            return []
        
        data = response.json()
        
        # Basic publication info
        title = data.get("title", "Unknown title")
        print(f"Title: {title}")
        
        # Process authorships
        authorships = data.get("authorships", [])
        print(f"Found {len(authorships)} authors")
        
        author_affiliations = []
        for author_entry in authorships:
            author_name = author_entry.get("author", {}).get("display_name", "Unknown")
            institutions = author_entry.get("institutions", [])
            
            # If no institutions, add with unknown institution
            if not institutions:
                affiliation = {
                    "author_name": author_name,
                    "institution_name": "Unknown Institution",
                    "city": "Unknown",
                    "country": "Unknown"
                }
                author_affiliations.append(affiliation)
                print(f"  - {author_name}: Unknown Institution (Unknown, Unknown)")
                continue
                
            for inst in institutions:
                institution_name = inst.get("display_name", "Unknown Institution")
                city = inst.get("geo", {}).get("city", "Unknown")
                country = inst.get("geo", {}).get("country", "Unknown")
                
                affiliation = {
                    "author_name": author_name,
                    "institution_name": institution_name,
                    "city": city,
                    "country": country
                }
                author_affiliations.append(affiliation)
                print(f"  - {author_name}: {institution_name} ({city}, {country})")
        
        return author_affiliations
    
    except Exception as e:
        print(f"Error for DOI {doi}: {e}")
        return []

def main():
    # Example DOIs from DBLP database
    example_dois = [
        "10.1145/996566.996732",  # from your sample data
        "10.1145/3061639.3062325" # from your sample data
    ]
    
    print("Demo: Fetching Institution Data from OpenAlex API\n")
    
    for doi in example_dois:
        print(f"\n{'='*60}")
        print(f"Processing DOI: {doi}")
        print(f"{'='*60}")
        
        affiliations = get_openalex_data_from_doi(doi)
        print(f"Total affiliations found: {len(affiliations)}")
        
        # Be nice to the API
        time.sleep(1)
    
    print("\nDemo complete!")

if __name__ == "__main__":
    main() 