
import csv

# Combine all the parts into complete files
complete_providers = providers_part1 + providers_part2 + providers_part3 + providers_part4
complete_run = run_content + run_content_part2

# Create a comprehensive CSV with all file contents
files_data = [
    {
        'filename': 'backend/scraper/__init__.py',
        'content': init_content,
        'description': 'Module initialization with exports'
    },
    {
        'filename': 'backend/scraper/providers.py',
        'content': complete_providers,
        'description': 'All provider classes including YouTube, RSS, Wikipedia, GOV.UK, Hansard, and Generic'
    },
    {
        'filename': 'backend/scraper/db.py',
        'content': db_content,
        'description': 'Database layer for storing scraped content'
    },
    {
        'filename': 'backend/scraper/embeddings.py',
        'content': embeddings_content,
        'description': 'Embedding generation using sentence-transformers'
    },
    {
        'filename': 'backend/scraper/run.py',
        'content': complete_run,
        'description': 'CLI entrypoint for running scrapers'
    },
    {
        'filename': 'requirements.txt (additions)',
        'content': requirements_additions,
        'description': 'Python dependencies to add to requirements.txt'
    },
    {
        'filename': 'tests/test_scraper.py',
        'content': test_scraper_content,
        'description': 'Unit tests for scraper module'
    },
    {
        'filename': 'README.md (section to add)',
        'content': readme_section,
        'description': 'Documentation section for README'
    }
]

# Write to CSV
csv_filename = 'scraper_module_files.csv'
with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['filename', 'description', 'content']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for file_data in files_data:
        writer.writerow(file_data)

print(f"Created {csv_filename} with all file contents")
print(f"\nFile statistics:")
for file_data in files_data:
    lines = file_data['content'].count('\n') + 1
    chars = len(file_data['content'])
    print(f"  {file_data['filename']}: {lines} lines, {chars} characters")

print(f"\nTotal code: {sum(len(f['content']) for f in files_data)} characters")
