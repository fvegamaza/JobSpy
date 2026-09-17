import csv
import re
import sys
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs

raw_titles = sys.argv[1] if len(sys.argv) > 1 else "data scientist"
raw_location = sys.argv[2] if len(sys.argv) > 2 else "Austria"
terms = [t.strip() for t in re.split(r"[,+/]", raw_titles) if t.strip()]
places = [p.strip() for p in re.split(r"[+/]", raw_location) if p.strip()]
search_title = " + ".join(terms)
search_location = " + ".join(places)

parts = []
for term in terms:
    for place in places:
        print(f"Searching {term!r} in {place}")
        df = scrape_jobs(
            site_name=["indeed", "linkedin", "glassdoor", "google"],
            search_term=term,
            google_search_term=f"{term} jobs in {place} posted in the last week",
            location=place,
            distance=400,
            results_wanted=50,
            hours_old=168,
            country_indeed="Austria",
            linkedin_fetch_description=True,
            verbose=1,
        )
        if df is not None and not df.empty:
            parts.append(df)

jobs = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
if "id" in jobs.columns:
    jobs = jobs.drop_duplicates(subset=["id"])

if not jobs.empty:
    jobs["search_title"] = search_title
    jobs["search_location"] = search_location

out_dir = Path("searches")
out_dir.mkdir(exist_ok=True)
slug = re.sub(r"[^a-z0-9]+", "_", f"{search_title}_{search_location}".lower()).strip("_")
output_path = out_dir / f"{slug}.csv"
jobs.to_csv(
    output_path,
    quoting=csv.QUOTE_NONNUMERIC,
    escapechar="\\",
    index=False,
)

print(f"Found {len(jobs)} jobs")
print(f"Saved results to {output_path}")

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from franco.process import process_file
    skipped, scored = process_file(output_path)
    print(f"Franco: skipped {skipped}, scored {scored}")
except Exception as e:
    print(f"franco process skipped: {e}")
if not jobs.empty:
    columns = [
        column
        for column in ["site", "title", "company", "location", "date_posted", "job_url"]
        if column in jobs.columns
    ]
    print(jobs[columns].to_string(index=False))
