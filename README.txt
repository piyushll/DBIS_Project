Conference Management (Premium Project)
Aryan Gupta (22B2255) Ashish Zantye (22B2217) Piyush Babar (22B3909) Shresth Verma (22B2211)

Tasks completed-

We have completed the part 1 of the project. We made the data schema which exists in data.ddl file which consists of 4 tables - publications, publication_authors, publication_editors 
and publication_citations with their primary key and necessary fields for access and query execution. Run script.sh file first and then dbms_load.py file is used to load the compressed .gz database into the schema to make postgresSQL database in the backend. We have also integrated indexing for faster access while query processing.
Once the data schema and corresponding dataset was uploaded in the backend, we started with writing frontend with HTML styling with CSS and backend with JS. Currently we have implemented conflict checker where a list of author ID and reviewer ID are input along with X,N,Y which act as hyperparameters. In the backend there is check if any of the reviewer has published any publication with any of the authors in past X years or more than N publications in last Y years. If conflicts are found corresponding author ID, reviewer ID pair is flagged as conflict. Thus we have successfully implemented the part 1 of the project 

Submitted files-

├── data.ddl
├── dbms_load.py
├── script.js (backend)
├── frontend/
│   ├── index
│   ├── styles/
│   │       └── style
├── script.sh

(other supporting files) 

How to Run ?

./script.sh (ensure right user details)
python3 dbms_load.py (ensure .gz file in right directory)
node script.js (check for correct db account)
run http://localhost:3000 on webserver 
u are ready to go ;)


Future Implementation-
In part 2, we are going to add conflict check to see whether reviewer and author work at same organization or have worked together at same organization in past N years. Also care would be taken to see if there is diversity in term of organization and city among the list of reviewers. 
Extra Planned implementation include but not restricted to - 
1. given a set of author ID will output a list of N (taken as input) reviewer IDs with no conflicts and have diversity so as to easy the authors while publishing. 
2. Add other viewing features - whether the 2 ID have published in past and what all they have published to make the interface more interactive
3. Integrate ChatGPT API such that natural language input by user would be processed to make SQL queries are run in background to output the result 

