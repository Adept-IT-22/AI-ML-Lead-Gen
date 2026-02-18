#!/usr/bin/env python3
"""
Script to REMOVE manual placeholder initialization in hiring ingestion fetch.py files.
Matches user request to use "automatic way" like funding module.
"""

import os
import re
from pathlib import Path

# Files to update
FILES_TO_UPDATE = [
    "ingestion_module/hiring/working_nomads/fetch.py",
    "ingestion_module/hiring/remotive/fetch.py",
    "ingestion_module/hiring/we_work_remotely/fetch.py",
    "ingestion_module/hiring/remote_frontend_jobs/fetch.py",
    "ingestion_module/hiring/python_org/fetch.py",
    "ingestion_module/hiring/remoteok/fetch.py",
    "ingestion_module/hiring/nodesk/fetch.py",
    "ingestion_module/hiring/jobspresso/fetch.py",
    "ingestion_module/hiring/jobicy/fetch.py",
    "ingestion_module/hiring/himalayas/fetch.py",
    "ingestion_module/hiring/four_day_week/fetch.py",
    "ingestion_module/hiring/berlin_startup_jobs/fetch.py",
    "ingestion_module/hiring/arc_dev/fetch.py",
    "ingestion_module/hiring/arbeitnow/fetch.py",
    "ingestion_module/hiring/active_jobs_db/fetch.py"
]

def update_file(filepath):
    """Remove placeholder initialization loop."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False

    # Regex to match the loop blocks
    # Pattern A: Includes company_name placeholder before loop
    pattern_a = r'(\s+# Placeholders\s+)?(\s+llm_results\["company_name"\]\.append\(""\)\s+)?\s+for key in \[[^\]]*"tags"[^\]]*\]:\s+if key in \[[^\]]*"tags"[^\]]*\]:\s+llm_results\[key\]\.append\(\[\]\)\s+else:\s+llm_results\[key\]\.append\(""\)'
    
    # Pattern B: Simple Loop
    pattern_b = r'\s+for key in \[[^\]]*"tags"[^\]]*\]:\s+if key in \[[^\]]*"tags"[^\]]*\]:\s+llm_results\[key\]\.append\(\[\]\)\s+else:\s+llm_results\[key\]\.append\(""\)'

    # Pattern C: Loop for active_jobs_db (might be different, actually active_jobs_db uses manual extraction logic which was fixed to auto-merge in step 435, so it might not have placeholders loop? 
    # Let's check active_jobs_db content from step 430.
    # It has: 
    #         # Placeholders
    #         for key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags", "city", "country"]:
    #             if key in ["company_decision_makers", "hiring_reasons", "job_roles", "tags"]:
    #                 llm_results[key].append([])
    #             else:
    #                 llm_results[key].append("")
    # YES it has placeholders loop.
    
    patterns = [pattern_a, pattern_b]
    
    for pattern in patterns:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            modified = True
            break
            
    # Also handle active_jobs_db specifically if needed? 
    # The patterns above should catch it if formatting is standard.

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function."""
    backend_dir = Path(__file__).parent
    updated_count = 0
    
    for relative_path in FILES_TO_UPDATE:
        filepath = backend_dir / relative_path
        
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}")
            continue
        
        try:
            if update_file(filepath):
                print(f"✅ Updated: {relative_path}")
                updated_count += 1
            else:
                print(f"ℹ️  No changes needed: {relative_path}")
        except Exception as e:
            print(f"❌ Error updating {relative_path}: {e}")
    
    print(f"\n🎉 Updated {updated_count} files!")

if __name__ == "__main__":
    main()
