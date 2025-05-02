const express = require('express');
const bodyParser = require('body-parser');
const { Pool } = require('pg');
const cors = require('cors');

const app = express();
const port = 3000;

const pool = new Pool({
    user: 'postgres',
    host: 'localhost',
    database: 'dblp15',
    password: 'Piyush@123',
    port: 5432,
});

app.use(bodyParser.json());
app.use(cors());
app.use(express.static('frontend'));

app.post('/check-conflicts', async (req, res) => {
    const { authorIds, reviewerIds, years, coauthorThreshold, yearThreshold } = req.body;

    // Log the input values for debugging
    console.log('Received Input:');
    console.log('Author IDs:', authorIds);
    console.log('Reviewer IDs:', reviewerIds);
    console.log('Years:', years);
    console.log('Coauthor Threshold:', coauthorThreshold);
    console.log('Year Threshold:', yearThreshold);

    try {
        // Conflict 1: Coauthorship in the last X years
        const recentCoauthorshipConflicts = await pool.query(`
            SELECT pa.person_key AS author_id, pr.person_key AS reviewer_id, pa.publication_key AS publication_key
            FROM publication_authors pa
            JOIN publication_authors pr ON pr.publication_key = pa.publication_key
            JOIN publications p ON pa.publication_key = p.key
            WHERE pa.person_key = ANY($1::text[])
              AND pr.person_key = ANY($2::text[])
              AND p.year >= EXTRACT(YEAR FROM CURRENT_DATE) - $3::integer
        `, [authorIds, reviewerIds, years]);

        // Conflict 2: Coauthoring more than N papers in the last Y years
        const frequentCoauthorshipConflicts = await pool.query(`
            SELECT pa.person_key AS author_id, pr.person_key AS reviewer_id, COUNT(pa.publication_key) AS coauthored_papers
            FROM publication_authors pa
            JOIN publication_authors pr ON pr.publication_key = pa.publication_key
            JOIN publications p ON pa.publication_key = p.key
            WHERE pa.person_key = ANY($1::text[])
              AND pr.person_key = ANY($2::text[])
              AND p.year >= EXTRACT(YEAR FROM CURRENT_DATE) - $3::integer
            GROUP BY pa.person_key, pr.person_key
            HAVING COUNT(pa.publication_key) >= $4::integer
        `, [authorIds, reviewerIds, yearThreshold, coauthorThreshold]);

        const conflicts = {
            recentCoauthorshipConflicts: recentCoauthorshipConflicts.rows,
            frequentCoauthorshipConflicts: frequentCoauthorshipConflicts.rows,
        };

        if (conflicts.recentCoauthorshipConflicts.length === 0 && conflicts.frequentCoauthorshipConflicts.length === 0) {
            return res.json({ message: "No conflicts found." });
        }

        res.json({ conflicts });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// New route for viewing table data
app.get('/view-table', async (req, res) => {
    const { tableName, limit } = req.query;
    const rowLimit = parseInt(limit) || 10; // Default to 10 rows if limit is not provided

    // List of allowed tables for security
    const allowedTables = ['publications', 'persons', 'publication_authors', 'publication_editors', 'publication_citations'];
    
    if (!tableName || !allowedTables.includes(tableName)) {
        return res.status(400).json({ error: 'Invalid table name' });
    }

    try {
        // Get table columns
        const columnQuery = await pool.query(`
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        `, [tableName]);
        
        // Get table data
        const dataQuery = await pool.query(`
            SELECT *
            FROM ${tableName}
            LIMIT $1
        `, [rowLimit]);

        // Get total count
        const countQuery = await pool.query(`
            SELECT COUNT(*) as total
            FROM ${tableName}
        `);

        res.json({
            columns: columnQuery.rows,
            data: dataQuery.rows,
            totalRows: parseInt(countQuery.rows[0].total),
            returnedRows: dataQuery.rows.length
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// Get list of available tables
app.get('/tables', async (req, res) => {
    try {
        const query = await pool.query(`
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        `);
        
        res.json({
            tables: query.rows.map(row => row.tablename)
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// API route for recommending reviewers with no conflicts and diversity
app.post('/recommend-reviewers', async (req, res) => {
    const { authorIds, count, years, coauthorThreshold, yearThreshold } = req.body;
    
    // Log the input values for debugging
    console.log('Received reviewer recommendation request:');
    console.log('Author IDs:', authorIds);
    console.log('Count:', count);
    console.log('Years:', years);
    console.log('Coauthor Threshold:', coauthorThreshold);
    console.log('Year Threshold:', yearThreshold);
    
    try {
        // Step 1: Get all potential reviewers (all authors in the system)
        const potentialReviewers = await pool.query(`
            SELECT DISTINCT person_key, COUNT(DISTINCT publication_key) as publication_count 
            FROM publication_authors
            GROUP BY person_key
            HAVING COUNT(DISTINCT publication_key) > 2  -- Only consider authors with multiple publications
            ORDER BY publication_count DESC
            LIMIT 1000  -- Limit to top 1000 most prolific authors for performance
        `);
        
        // Step 2: Exclude authors with conflicts
        // Find authors who have co-authored with the given authors in the last X years
        const coauthorConflicts = await pool.query(`
            SELECT DISTINCT pa2.person_key AS reviewer_id
            FROM publication_authors pa1
            JOIN publication_authors pa2 ON pa1.publication_key = pa2.publication_key 
                                       AND pa1.person_key != pa2.person_key
            JOIN publications p ON pa1.publication_key = p.key
            WHERE pa1.person_key = ANY($1::text[])
              AND p.year >= EXTRACT(YEAR FROM CURRENT_DATE) - $2::integer
        `, [authorIds, years]);
        
        // Find authors who have co-authored multiple papers with the given authors
        const frequentCoauthorConflicts = await pool.query(`
            SELECT pa2.person_key AS reviewer_id
            FROM publication_authors pa1
            JOIN publication_authors pa2 ON pa1.publication_key = pa2.publication_key 
                                       AND pa1.person_key != pa2.person_key
            JOIN publications p ON pa1.publication_key = p.key
            WHERE pa1.person_key = ANY($1::text[])
              AND p.year >= EXTRACT(YEAR FROM CURRENT_DATE) - $2::integer
            GROUP BY pa2.person_key
            HAVING COUNT(DISTINCT pa1.publication_key) >= $3::integer
        `, [authorIds, yearThreshold, coauthorThreshold]);
        
        // Create a set of all reviewer IDs with conflicts
        const conflictReviewers = new Set();
        
        // Add the input author IDs to conflicts (can't review your own paper)
        authorIds.forEach(id => conflictReviewers.add(id));
        
        // Add coauthor conflicts
        coauthorConflicts.rows.forEach(row => conflictReviewers.add(row.reviewer_id));
        
        // Add frequent coauthor conflicts
        frequentCoauthorConflicts.rows.forEach(row => conflictReviewers.add(row.reviewer_id));
        
        // Step 3: Filter out the conflicts from potential reviewers
        const eligibleReviewers = potentialReviewers.rows.filter(
            reviewer => !conflictReviewers.has(reviewer.person_key)
        );
        
        // Step 4: Get additional information for diversity analysis
        const reviewerDetailsPromises = eligibleReviewers.slice(0, Math.min(100, eligibleReviewers.length)).map(async reviewer => {
            // Get publication venues (journals/conferences) for diversity
            const venuesQuery = await pool.query(`
                SELECT DISTINCT p.journal, COUNT(*) as count
                FROM publication_authors pa
                JOIN publications p ON pa.publication_key = p.key
                WHERE pa.person_key = $1 AND p.journal IS NOT NULL
                GROUP BY p.journal
                ORDER BY count DESC
                LIMIT 3
            `, [reviewer.person_key]);
            
            // Get years of activity
            const yearsQuery = await pool.query(`
                SELECT MIN(p.year) as first_year, MAX(p.year) as last_year
                FROM publication_authors pa
                JOIN publications p ON pa.publication_key = p.key
                WHERE pa.person_key = $1 AND p.year IS NOT NULL
            `, [reviewer.person_key]);
            
            // Get coauthors count
            const coauthorsQuery = await pool.query(`
                SELECT COUNT(DISTINCT pa2.person_key) as coauthor_count
                FROM publication_authors pa1
                JOIN publication_authors pa2 ON pa1.publication_key = pa2.publication_key 
                                           AND pa1.person_key != pa2.person_key
                WHERE pa1.person_key = $1
            `, [reviewer.person_key]);
            
            return {
                person_key: reviewer.person_key,
                publication_count: reviewer.publication_count,
                venues: venuesQuery.rows,
                years_active: yearsQuery.rows[0],
                coauthor_count: coauthorsQuery.rows[0]?.coauthor_count || 0
            };
        });
        
        const reviewerDetails = await Promise.all(reviewerDetailsPromises);
        
        // Step 5: Apply diversity algorithm
        // - Score reviewers based on diverse venues
        // - Ensure mix of seniority (years active)
        // - Avoid reviewers who all have similar publication patterns
        
        // Count unique venues across all reviewers for diversity scoring
        const venueFrequency = {};
        reviewerDetails.forEach(reviewer => {
            reviewer.venues.forEach(venue => {
                if (!venueFrequency[venue.journal]) {
                    venueFrequency[venue.journal] = 0;
                }
                venueFrequency[venue.journal]++;
            });
        });
        
        // Score each reviewer
        reviewerDetails.forEach(reviewer => {
            // Base score from publication count (experience)
            let score = Math.min(reviewer.publication_count / 10, 5); // Cap at 5 points
            
            // Venue diversity score
            let venueDiversityScore = 0;
            reviewer.venues.forEach(venue => {
                // Venues that are less common among other reviewers get higher scores
                const venueRarity = 1 / (venueFrequency[venue.journal] || 1);
                venueDiversityScore += venueRarity * 2;
            });
            score += venueDiversityScore;
            
            // Experience score based on years active
            if (reviewer.years_active && reviewer.years_active.first_year && reviewer.years_active.last_year) {
                const yearsActive = reviewer.years_active.last_year - reviewer.years_active.first_year + 1;
                // Sqrt for diminishing returns on very long careers
                score += Math.min(Math.sqrt(yearsActive) / 2, 3);
            }
            
            // Collaboration network size (more connections = greater awareness of the field)
            score += Math.min(Math.log10(reviewer.coauthor_count || 1), 2);
            
            reviewer.score = Math.round(score * 100) / 100;
        });
        
        // Sort by score
        reviewerDetails.sort((a, b) => b.score - a.score);
        
        // Step 6: Select top N reviewers, but ensure diversity
        const selectedReviewers = [];
        const selectedVenues = new Set();
        let nextCandidateIndex = 0;
        
        // Helper to check if a reviewer adds diversity
        const addsDiversity = (reviewer) => {
            // If we have fewer than 2 reviewers, any will do
            if (selectedReviewers.length < 2) return true;
            
            // Check if this reviewer publishes in venues we haven't covered yet
            for (const venue of reviewer.venues) {
                if (!selectedVenues.has(venue.journal)) {
                    return true;
                }
            }
            
            return false;
        };
        
        // First, select the top scored reviewer
        if (reviewerDetails.length > 0) {
            const topReviewer = reviewerDetails[0];
            selectedReviewers.push(topReviewer);
            topReviewer.venues.forEach(venue => selectedVenues.add(venue.journal));
            nextCandidateIndex = 1;
        }
        
        // Then, select a mix of high scoring and diverse reviewers
        while (selectedReviewers.length < count && nextCandidateIndex < reviewerDetails.length) {
            // Every other pick, prioritize diversity over pure score
            if (selectedReviewers.length % 2 === 1 && selectedReviewers.length < count - 1) {
                // Look for a reviewer who adds diversity
                let diverseReviewerFound = false;
                
                for (let i = nextCandidateIndex; i < reviewerDetails.length; i++) {
                    const reviewer = reviewerDetails[i];
                    if (addsDiversity(reviewer)) {
                        selectedReviewers.push(reviewer);
                        reviewer.venues.forEach(venue => selectedVenues.add(venue.journal));
                        reviewerDetails.splice(i, 1);
                        diverseReviewerFound = true;
                        break;
                    }
                }
                
                // If no diverse reviewer found, just pick the next best
                if (!diverseReviewerFound && nextCandidateIndex < reviewerDetails.length) {
                    selectedReviewers.push(reviewerDetails[nextCandidateIndex]);
                    reviewerDetails[nextCandidateIndex].venues.forEach(venue => selectedVenues.add(venue.journal));
                    nextCandidateIndex++;
                }
            } else {
                // Pick next best by score
                selectedReviewers.push(reviewerDetails[nextCandidateIndex]);
                reviewerDetails[nextCandidateIndex].venues.forEach(venue => selectedVenues.add(venue.journal));
                nextCandidateIndex++;
            }
        }
        
        // Step 7: Get names for the selected reviewer IDs
        const reviewerIds = selectedReviewers.map(r => r.person_key);
        const namesQuery = await pool.query(`
            SELECT key, name FROM persons
            WHERE key = ANY($1::text[])
        `, [reviewerIds]);
        
        // Create a map of ID to name
        const nameMap = {};
        namesQuery.rows.forEach(row => {
            nameMap[row.key] = row.name;
        });
        
        // Add names to the selected reviewers
        selectedReviewers.forEach(reviewer => {
            reviewer.name = nameMap[reviewer.person_key] || 'Unknown';
        });
        
        res.json({
            recommendedReviewers: selectedReviewers,
            totalEligible: eligibleReviewers.length,
            totalWithConflicts: conflictReviewers.size - authorIds.length
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.get('/', (req, res) => {
    res.send('Welcome to the Author-Reviewer Conflict Checker API!');
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});