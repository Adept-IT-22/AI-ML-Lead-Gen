#!/usr/bin/env python3
"""
Script to add 'painpoints' and 'service' to placeholder initialization in hiring ingestion fetch.py files.
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
    # active_jobs_db handle separately if needed (it has a different structure)
]

def update_file(filepath):
    """Update a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    # Update loop list
    # Look for list ending with "city", "country" or just "country"
    loop_pattern = r'(for key in \[.*?"city", "country")(\]:)'
    if re.search(loop_pattern, content):
        # Check if painpoints already there
        if '"painpoints"' not in re.search(loop_pattern, content).group(1):
             content = re.sub(loop_pattern, r'\1, "painpoints", "service"\2', content)
             modified = True
    
    # Update if condition list
    # Look for list ending with "tags"
    if_pattern = r'(if key in \[.*?"tags")(\]:)'
    if re.search(if_pattern, content):
        if '"painpoints"' not in re.search(if_pattern, content).group(1):
            content = re.sub(if_pattern, r'\1, "painpoints"\2', content)
            modified = True

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
