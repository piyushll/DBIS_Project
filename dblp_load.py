#!/usr/bin/env python3
from lxml import etree
import psycopg2
import sys
import gzip
import os
import logging
import traceback
from datetime import datetime

# --------------------------
# Configuration
# --------------------------
DB_NAME = "dblp15"
DB_USER = "postgres"
DB_PASSWORD = "Piyush@123"
DB_HOST = "localhost"
DB_PORT = "5432"
XML_FILE = "./dblp.xml.gz"

# --------------------------
# Publication Types
# --------------------------
PUB_TYPES = {
    "article", "inproceedings", "proceedings", "book", "incollection",
    "phdthesis", "mastersthesis", "www", "data"
}

# --------------------------
# Database Connection
# --------------------------
def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# --------------------------
# Helper Functions
# --------------------------
def safe_date(date_str):
    """Convert date string to date object safely."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

# --------------------------
# Publication Processing
# --------------------------
def insert_publication(cur, pub_data):
    # First, properly handle data types for numeric fields
    for field in ['year', 'month', 'volume', 'number']:
        if field in pub_data and pub_data[field] == '':
            pub_data[field] = None  # Convert empty strings to None for numeric fields
        elif field in pub_data and field == 'year':
            # Try to convert year to integer
            try:
                pub_data[field] = int(pub_data[field])
            except (ValueError, TypeError):
                pub_data[field] = None
    
    # Continue with your existing insertion logic
    columns = []
    values = []
    for key, value in pub_data.items():
        if value is not None:
            columns.append(key)
            values.append(value)
    
    sql = f"""
    INSERT INTO publications ({", ".join(columns)})
    VALUES ({", ".join(['%s']*len(values))})
    ON CONFLICT (key) DO NOTHING
    """
    # print(f"Executing SQL: {sql} with values {values}")
    cur.execute(sql, values)


def process_publication_element(elem, cur):
    # Map for publication fields
    pub_data = {
        "key": elem.get("key"),
        "type": elem.tag,
        "title": None,
        "booktitle": None,
        "pages": None,
        "year": None,
        "volume": None,
        "number": None,
        "month": None,
        "journal": None,
        "publisher": None,
        "note": None,
        "crossref": None,
        "isbn": None,
        "series": None,
        "school": None,
        "chapter": None,
        "publnr": None,
        "url": None,
        "ee": None,
        "address": None,
        "stream": None,
        "rel": None,
        "mdate": safe_date(elem.get("mdate")),
        "cdate": safe_date(elem.get("cdate")),
        "publtype": elem.get("publtype"),
        "reviewid": elem.get("reviewid"),
        "rating": elem.get("rating"),
        "cdrom": None
    }

    authors = []
    editors = []
    citations = []
    
    # Process child elements
    for child in elem:
        tag = child.tag
        # print(f"Processing child {tag}")
        text = "".join(child.itertext()).strip() 
        
        # Handle authors
        if tag == "author":
            authors.append({
                "name": text,
                "position": len(authors),
                "aux": child.get("aux"),
                "bibtex": child.get("bibtex"),
                "orcid": child.get("orcid"),
                "label": child.get("label"),
                "type": child.get("type")
            })
        # Handle editors
        elif tag == "editor":
            editors.append({
                "name": text,
                "position": len(editors),
                "aux": child.get("aux"),
                "orcid": child.get("orcid"),
                "label": child.get("label"),
                "type": child.get("type")
            })
        # Handle citations
        elif tag == "cite":
            citations.append({
                "cite": text,
                "ref": child.get("ref"),
                "aux": child.get("aux"),
                "label": child.get("label"),
                "type": child.get("type")
            })
        # Handle scalar fields
        elif tag in pub_data and pub_data[tag] is None:
            pub_data[tag] = text

    # Insert publication
    insert_publication(cur, pub_data)
    
    # Process authors
    for author in authors:
        if author["name"]:
            author_key = f"person/{author['name'].replace(' ', '_')}"
            
            # Insert person
            cur.execute("""
                INSERT INTO persons (key, name)
                VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (author_key, author["name"]))
            
            # Insert publication-author relationship
            cur.execute("""
                INSERT INTO publication_authors 
                (publication_key, person_key, position, aux, bibtex, orcid, label, type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (publication_key, person_key, position) DO NOTHING
            """, (
                pub_data["key"], 
                author_key, 
                author["position"],
                author["aux"],
                author["bibtex"],
                author["orcid"],
                author["label"],
                author["type"]
            ))
    
    # Process editors
    for editor in editors:
        if editor["name"]:
            editor_key = f"person/{editor['name'].replace(' ', '_')}"
            
            # Insert person
            cur.execute("""
                INSERT INTO persons (key, name)
                VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (editor_key, editor["name"]))
            
            # Insert publication-editor relationship
            cur.execute("""
                INSERT INTO publication_editors 
                (publication_key, person_key, position, aux, orcid, label, type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (publication_key, person_key, position) DO NOTHING
            """, (
                pub_data["key"], 
                editor_key, 
                editor["position"],
                editor["aux"],
                editor["orcid"],
                editor["label"],
                editor["type"]
            ))
    
    # Process citations
    for citation in citations:
        if citation["cite"] is not None:
            cur.execute("""
                INSERT INTO publication_citations 
                (publication_key, cite, ref, aux, label, type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                pub_data["key"], 
                citation["cite"],
                citation["ref"],
                citation["aux"],
                citation["label"],
                citation["type"]
            ))

# --------------------------
# Person Processing
# --------------------------
def process_person_element(elem, cur):
    key = elem.get("key")
    if not key:
        return
    
    # Find name from author children
    author_elem = elem.find("author")
    name = author_elem.text.strip() if author_elem is not None and author_elem.text else key
    
    # Insert person
    cur.execute("""
        INSERT INTO persons (key, name, mdate, cdate)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (key) DO NOTHING
    """, (
        key, 
        name,
        safe_date(elem.get("mdate")),
        safe_date(elem.get("cdate"))
    ))

# --------------------------
# Main Processing
# --------------------------
def main():
    conn = connect_db()
    cur = conn.cursor()
    
    # Open the .gz file and parse it
    with gzip.open(XML_FILE, "rb") as f:
        context = etree.iterparse(f, events=("end",), huge_tree=True)
        
        batch_size = 1000
        count = 0
        person_count = 0
        
        for event, elem in context:
            try:
                if elem.tag in PUB_TYPES:
                    # Process publication
                    process_publication_element(elem, cur)
                    count += 1
                    
                    if count % batch_size == 0:
                        conn.commit()
                        print(f"Processed {count} publications, {person_count} persons")
                
                elif elem.tag == "person":
                    # Process person
                    process_person_element(elem, cur)
                    person_count += 1
                    
                    if person_count % batch_size == 0:
                        conn.commit()
                
            except Exception as e:
                print(f"Error processing {elem.tag} {elem.get('key', '')}: {str(e)}")
                traceback.print_exc()
                conn.rollback()
            
            # Clear element to free memory
            # elem.clear()
            
            # # Clear preceding siblings
            # while elem.getprevious() is not None:
            #     del elem.getparent()[0]
        
        # Final commit
        conn.commit()
        print(f"Total processed: {count} publications, {person_count} persons")
        
        # Create indexes if needed
        try:
            print("Creating indexes...")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pub_type ON publications(type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pub_year ON publications(year)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_person_name ON persons(name)")
            conn.commit()
            print("Indexes created successfully")
        except Exception as e:
            print(f"Error creating indexes: {str(e)}")
        
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
