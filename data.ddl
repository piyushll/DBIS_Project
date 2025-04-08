/*
 * PostgreSQL Database Schema for DBLP Computer Science Bibliography
 * Created: Tuesday, April 08, 2025, 10:45 AM IST
 *
 * This schema is designed to store bibliographic data from the DBLP Computer Science Bibliography,
 * based on the DTD from https://dblp.org/xml/dblp.dtd
 *
 * The database uses a single table approach for all publication types with junction tables
 * for handling many-to-many relationships with authors and editors.
 */

-- Drop tables if they exist
DROP TABLE IF EXISTS publication_citations;
DROP TABLE IF EXISTS publication_editors;
DROP TABLE IF EXISTS publication_authors;
DROP TABLE IF EXISTS persons;
DROP TABLE IF EXISTS publications;

-- Publications table - stores all publication types with a discriminator field
CREATE TABLE publications (
    key VARCHAR(255) PRIMARY KEY,                -- Unique identifier for the publication
    type VARCHAR(50) NOT NULL,                   -- Type of publication ('article', 'book', 'inproceedings', etc.)
    title TEXT,                                  -- Title of the publication
    booktitle TEXT,                              -- Title of the book/proceedings containing the publication
    pages VARCHAR(100),                          -- Page range of the publication
    year INTEGER,                                -- Year of publication
    volume VARCHAR(50),                          -- Volume number for journals or series
    number VARCHAR(50),                          -- Issue number for journals
    month VARCHAR(20),                           -- Month of publication
    journal VARCHAR(255),                        -- Journal name for articles
    publisher VARCHAR(255),                      -- Publisher name
    note TEXT,                                   -- Additional notes about the publication
    crossref VARCHAR(255),                       -- Cross-reference to another publication
    isbn VARCHAR(50),                            -- ISBN number
    series VARCHAR(255),                         -- Series name for books or proceedings
    school VARCHAR(255),                         -- School name for theses
    chapter VARCHAR(50),                         -- Chapter number for book sections
    publnr VARCHAR(100),                         -- Publisher's identifier
    url TEXT,                                    -- URL pointing to the publication
    ee TEXT,                                     -- Electronic edition URL
    address TEXT,                                -- Publication address/location
    stream TEXT,                                 -- Stream information (without attributes)
    rel TEXT,                                    -- Relationship information (without attributes)
    mdate DATE,                                  -- Last modification date
    cdate DATE,                                  -- Creation date
    publtype VARCHAR(255),                       -- Publication type qualifier
    reviewid VARCHAR(255),                       -- Review identifier
    rating VARCHAR(50),                          -- Publication rating
    cdrom VARCHAR(255)                           -- CD-ROM information
);

-- Persons table - for authors and editors
CREATE TABLE persons (
    key VARCHAR(255) PRIMARY KEY,                -- Unique identifier for the person
    name VARCHAR(255) NOT NULL,                  -- Person's name
    mdate DATE,                                  -- Last modification date
    cdate DATE                                   -- Creation date
);

-- Authors junction table - many-to-many relationship between publications and authors
CREATE TABLE publication_authors (
    id SERIAL PRIMARY KEY,                       -- Auto-incrementing primary key
    publication_key VARCHAR(255) REFERENCES publications(key) ON DELETE CASCADE,
    person_key VARCHAR(255) REFERENCES persons(key) ON DELETE CASCADE,
    position INTEGER NOT NULL,                   -- To maintain order of authors
    aux TEXT,                                    -- Auxiliary information
    bibtex TEXT,                                 -- BibTeX information
    orcid VARCHAR(50),                           -- ORCID identifier
    label TEXT,                                  -- Label information
    type VARCHAR(100),                           -- Author type
    UNIQUE (publication_key, person_key, position)
);

-- Editors junction table - many-to-many relationship between publications and editors
CREATE TABLE publication_editors (
    id SERIAL PRIMARY KEY,                       -- Auto-incrementing primary key
    publication_key VARCHAR(255) REFERENCES publications(key) ON DELETE CASCADE,
    person_key VARCHAR(255) REFERENCES persons(key) ON DELETE CASCADE,
    position INTEGER NOT NULL,                   -- To maintain order of editors
    aux TEXT,                                    -- Auxiliary information
    orcid VARCHAR(50),                           -- ORCID identifier
    label TEXT,                                  -- Label information
    type VARCHAR(100),                           -- Editor type
    UNIQUE (publication_key, person_key, position)
);

-- Citations table - for citations between publications
CREATE TABLE publication_citations (
    id SERIAL PRIMARY KEY,                       -- Auto-incrementing primary key
    publication_key VARCHAR(255) REFERENCES publications(key) ON DELETE CASCADE,
    cite TEXT NOT NULL,                          -- Citation text
    ref VARCHAR(255),                            -- Reference to cited publication
    aux TEXT,                                    -- Auxiliary information
    label TEXT,                                  -- Label information
    type VARCHAR(100)                            -- Citation type
);

-- Create indexes for efficient lookups
CREATE INDEX idx_publication_type ON publications(type);
CREATE INDEX idx_publication_year ON publications(year);
CREATE INDEX idx_publication_title ON publications(title);
CREATE INDEX idx_publication_journal ON publications(journal);
CREATE INDEX idx_person_name ON persons(name);
CREATE INDEX idx_publication_authors_pub ON publication_authors(publication_key);
CREATE INDEX idx_publication_authors_person ON publication_authors(person_key);
CREATE INDEX idx_publication_editors_pub ON publication_editors(publication_key);
CREATE INDEX idx_publication_editors_person ON publication_editors(person_key);
