# iLearning Data coursework

Python data-engineering coursework: common Tasks 1–3, relational book ingestion (3.5), bookstore analytics (4), a Google Sheets mine generator and analytics dashboard (5), and a PostgreSQL stored-procedure contact generator (6).

Read START_HERE_RU.md for local setup, STATUS.md for current verification and unfinished requirements, and each task's README_RU.md for its explanation and study topics. Code contains no authored comments or docstrings; documentation is separate.

The dashboard includes precomputed results so it can display the data-analysis parts without loading the original datasets. Original course input files are included in the private delivery archive, but excluded from the public source repository. For a fresh ETL run, obtain the instructor's inputs and place them in the documented data/input directories.

Task 4's live AI integration is not complete. Public deployment and submission must not be inferred from passing local checks. The application reports the missing AI configuration explicitly.

The supplied Dockerfile starts Python and a loopback-only PostgreSQL instance, importing the fixed lookup data on startup. Generated contacts are reproducible; the database is disposable and reconstructed from the included dictionaries. This container design is intended for this coursework, not production customer data.

Lookup word sources: Faker (MIT) and GeoNames cities (CC BY 4.0). See task6/documentation.html and THIRD_PARTY.md.
