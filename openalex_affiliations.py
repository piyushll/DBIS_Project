import psycopg2
import requests
import time
import os
import re
from dotenv import load_dotenv
import sys
import json
import datetime
import logging

# Set up logging with reduced verbosity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("openalex_affiliation.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables if any
load_dotenv()

# Database connection parameters
DB_PARAMS = {
    'dbname': os.getenv('DB_NAME', 'dblp15'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'Piyush@123'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# OpenAlex API settings
OPENALEX_HEADERS = {
    "User-Agent": "DBMS_Project/22B2255_22B2217_22B3909_22B2211@email.com"  # Use your actual email
}

# Checkpoint file
CHECKPOINT_FILE = "affiliation_checkpoint.json"

# Batch size for processing
BATCH_SIZE = 50

# Create the author_affiliations table if it doesn't exist
CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS author_affiliations (
    id SERIAL PRIMARY KEY,
    publication_key TEXT REFERENCES publications(key),
    author_key TEXT REFERENCES persons(key),
    doi TEXT,
    author_name TEXT,
    institution_name TEXT,
    city TEXT,
    country TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(publication_key, author_key, institution_name)
);
"""

def connect_to_db():
    """Connect to the PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        logging.error(f"Error connecting to database: {e}")
        sys.exit(1)

def setup_table(conn):
    """Create the affiliations table if it doesn't exist"""
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_TABLE_QUERY)
        conn.commit()
        logging.info("Author affiliations table ready")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
        conn.rollback()
    finally:
        cursor.close()

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

def check_database_schema(conn):
    """Check database schema to debug issues"""
    cursor = conn.cursor()
    try:
        # Check if publications table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'publications'
            )
        """)
        if not cursor.fetchone()[0]:
            logging.error("Error: 'publications' table doesn't exist")
            return False
            
        # Get column names for publications
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'publications'
        """)
        columns = cursor.fetchall()
        logging.info("Publications table columns:")
        for col in columns:
            logging.info(f"  - {col[0]} ({col[1]})")
            
        # Check for ee column
        if not any(col[0] == 'ee' for col in columns):
            logging.error("Error: 'ee' column doesn't exist in publications table")
            return False
            
        # Check for publications with ee values
        cursor.execute("SELECT COUNT(*) FROM publications WHERE ee IS NOT NULL")
        count = cursor.fetchone()[0]
        logging.info(f"Found {count} publications with non-null ee values")
        
        # Get a sample publication with ee value
        cursor.execute("SELECT key, ee FROM publications WHERE ee IS NOT NULL LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            logging.info(f"Sample publication: {sample[0]}, ee: {sample[1]}")
        
        return True
    except Exception as e:
        logging.error(f"Error checking database schema: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()

def get_publications_with_doi(conn, limit=50, offset=0):
    """Get publications with DOIs that haven't been processed yet"""
    cursor = conn.cursor()
    try:
        # Use a literal value instead of parameter binding
        query = f"""
            SELECT p.key, p.ee
            FROM publications p
            LEFT JOIN author_affiliations aa ON p.key = aa.publication_key
            WHERE p.ee LIKE '%doi.org%'
            AND aa.id IS NULL
            ORDER BY p.key
            LIMIT {limit} OFFSET {offset}
        """
        cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            key = row[0]
            ee = row[1]
            doi = extract_doi_from_url(ee)
            if doi:
                results.append((key, doi))
        
        return results
    except Exception as e:
        logging.error(f"Error fetching publications: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cursor.close()

def count_unprocessed_publications(conn):
    """Count how many publications with DOIs are left to process"""
    cursor = conn.cursor()
    try:
        query = """
            SELECT COUNT(p.key)
            FROM publications p
            LEFT JOIN author_affiliations aa ON p.key = aa.publication_key
            WHERE p.ee LIKE '%doi.org%'
            AND aa.id IS NULL
        """
        cursor.execute(query)
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        logging.error(f"Error counting publications: {e}")
        return 0
    finally:
        cursor.close()

def get_authors_for_publication(conn, pub_key):
    """Get authors for a specific publication"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT pa.person_key, p.name
            FROM publication_authors pa
            JOIN persons p ON pa.person_key = p.key
            WHERE pa.publication_key = %s
        """, (pub_key,))
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error fetching authors: {e}")
        return []
    finally:
        cursor.close()

def get_openalex_data_from_doi(doi):
    """
    Queries OpenAlex API for a given DOI and returns a list of author affiliations with their cities.
    """
    api_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    
    try:
        # Reduced logging - don't log every DOI fetch
        response = requests.get(api_url, headers=OPENALEX_HEADERS)
        if response.status_code != 200:
            logging.error(f"Failed to fetch DOI {doi}: {response.status_code}")
            return []
        
        data = response.json()
        authorships = data.get("authorships", [])
        
        author_affiliations = []
        for author_entry in authorships:
            author_name = author_entry.get("author", {}).get("display_name", "Unknown")
            institutions = author_entry.get("institutions", [])
            
            # If no institutions, add with unknown institution
            if not institutions:
                author_affiliations.append({
                    "author_name": author_name,
                    "institution_name": "Unknown Institution",
                    "city": "Unknown",
                    "country": "Unknown"
                })
                continue
                
            for inst in institutions:
                institution_name = inst.get("display_name", "Unknown Institution")
                city = inst.get("geo", {}).get("city", "Unknown")
                country = inst.get("geo", {}).get("country", "Unknown")
                author_affiliations.append({
                    "author_name": author_name,
                    "institution_name": institution_name,
                    "city": city,
                    "country": country
                })
        
        return author_affiliations
    
    except Exception as e:
        logging.error(f"Error for DOI {doi}: {e}")
        return []

def save_affiliations(conn, publication_key, doi, affiliations, db_authors):
    """Save affiliations to database with best-effort author matching"""
    if not affiliations:
        # Reduced logging - don't log for each publication
        return 0
    
    cursor = conn.cursor()
    inserted_count = 0
    
    try:
        # Create a lookup for matching OpenAlex authors to DBLP authors by name similarity
        db_author_names = {author[1].lower(): author[0] for author in db_authors}
        
        for affiliation in affiliations:
            # Try to match author by name (simple case-insensitive match)
            author_name = affiliation["author_name"]
            author_key = None
            
            # Check for exact match first
            if author_name.lower() in db_author_names:
                author_key = db_author_names[author_name.lower()]
            else:
                # Try with partial matching
                for db_name, key in db_author_names.items():
                    # If the database name is part of the affiliation name or vice versa
                    if db_name in author_name.lower() or author_name.lower() in db_name:
                        author_key = key
                        break
            
            # If no match found, we'll still insert the record with NULL author_key
            insert_query = """
                INSERT INTO author_affiliations
                (publication_key, author_key, doi, author_name, institution_name, city, country)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (publication_key, author_key, institution_name) 
                DO NOTHING
            """
            
            cursor.execute(insert_query, (
                publication_key,
                author_key,
                doi,
                author_name,
                affiliation["institution_name"],
                affiliation["city"],
                affiliation["country"]
            ))
            inserted_count += 1
        
        conn.commit()
        # Reduced logging - don't log for each publication
        return inserted_count
    except Exception as e:
        logging.error(f"Error saving affiliations: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()

def load_checkpoint():
    """Load the checkpoint file if it exists"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint = json.load(f)
                logging.info(f"Loaded checkpoint: {checkpoint}")
                return checkpoint
        except Exception as e:
            logging.error(f"Error loading checkpoint: {e}")
    
    # Default checkpoint
    return {
        "last_offset": 0,
        "total_processed": 0,
        "total_affiliations": 0,
        "last_run": None
    }

def save_checkpoint(offset, total_processed, total_affiliations):
    """Save the current progress to the checkpoint file"""
    checkpoint = {
        "last_offset": offset,
        "total_processed": total_processed,
        "total_affiliations": total_affiliations,
        "last_run": datetime.datetime.now().isoformat()
    }
    
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f)
        logging.info(f"Saved checkpoint: {checkpoint}")
    except Exception as e:
        logging.error(f"Error saving checkpoint: {e}")

def format_time(seconds):
    """Format seconds into a readable time string"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.1f} minutes"
    else:
        return f"{seconds/3600:.1f} hours"

def main():
    """Main function to orchestrate the fetching and saving process"""
    logging.info("Starting affiliation data fetching process...")
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    offset = checkpoint["last_offset"]
    total_processed = checkpoint["total_processed"]
    total_affiliations = checkpoint["total_affiliations"]
    
    conn = connect_to_db()
    setup_table(conn)
    
    # Reduced logging for schema check
    if not check_database_schema(conn):
        logging.error("Database schema check failed. Exiting.")
        conn.close()
        return
    
    try:
        # Count total publications to process
        remaining = count_unprocessed_publications(conn)
        logging.info(f"Found {remaining} publications with DOIs left to process")
        
        if remaining == 0:
            logging.info("No new publications with DOIs to process.")
            return
        
        # Process in batches
        start_time = time.time()
        batch_count = 0
        last_progress_update = time.time()
        processed_since_last_update = 0
        
        while True:
            # Get a batch of publications to process
            publications = get_publications_with_doi(conn, BATCH_SIZE, offset)
            
            if not publications:
                logging.info("No more publications with DOIs found.")
                break
            
            batch_count += 1
            batch_start_time = time.time()
            batch_affiliations = 0
            
            logging.info(f"Processing batch {batch_count}: {len(publications)} publications (offset {offset})...")
            
            for i, (pub_key, doi) in enumerate(publications):
                if not doi:
                    continue
                
                # Get authors from DB for this publication
                db_authors = get_authors_for_publication(conn, pub_key)
                
                # Fetch affiliations from OpenAlex
                affiliations = get_openalex_data_from_doi(doi)
                
                # Save affiliations to database
                affiliations_added = save_affiliations(conn, pub_key, doi, affiliations, db_authors)
                batch_affiliations += affiliations_added
                total_affiliations += affiliations_added
                total_processed += 1
                processed_since_last_update += 1
                
                # Periodic progress updates (every 10 publications or 30 seconds)
                current_time = time.time()
                if processed_since_last_update >= 10 or (current_time - last_progress_update) >= 30:
                    # Progress within batch
                    progress = (i + 1) / len(publications) * 100
                    elapsed = current_time - start_time
                    pubs_per_second = total_processed / elapsed if elapsed > 0 else 0
                    
                    logging.info(f"Progress: {progress:.1f}% of current batch | Total: {total_processed}/{total_processed+remaining} | Rate: {pubs_per_second:.2f} pubs/sec")
                    last_progress_update = current_time
                    processed_since_last_update = 0
                
                # Reduced wait time between API calls
                # time.sleep(0.2)
            
            # Batch completed
            batch_time = time.time() - batch_start_time
            offset += len(publications)
            
            # Save checkpoint after each batch
            save_checkpoint(offset, total_processed, total_affiliations)
            
            # Batch summary
            logging.info(f"Batch {batch_count} completed in {format_time(batch_time)}")
            logging.info(f"Added {batch_affiliations} affiliations from {len(publications)} publications")
            
            # Overall progress
            elapsed = time.time() - start_time
            remaining = count_unprocessed_publications(conn)
            
            if remaining > 0 and total_processed > 0:
                # Estimate time remaining based on current rate
                rate = total_processed / elapsed
                estimated_remaining = remaining / rate
                logging.info(f"Overall progress: {total_processed} processed, {remaining} remaining")
                logging.info(f"Estimated time remaining: {format_time(estimated_remaining)}")
            
            # Check if we should continue
            if len(publications) < BATCH_SIZE or remaining == 0:
                break
        
        # Final summary
        total_time = time.time() - start_time
        logging.info(f"\nProcess complete in {format_time(total_time)}")
        logging.info(f"Processed {total_processed} publications, added {total_affiliations} affiliations")
        
    finally:
        conn.close()
        logging.info("Database connection closed")

if __name__ == "__main__":
    main() 