import re
import csv
from collections import defaultdict
from filter import get_exclude_patterns

def update_filter_csv(TMPOPT, user, csv_file):
    patterns = get_exclude_patterns(user)
    hits_dict = defaultdict(int)

    # Load existing CSV if present
    try:
        with open(csv_file, newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                pattern, count = row
                hits_dict[pattern] = int(count)
    except FileNotFoundError:
        pass  # CSV will be created

    # Count matches in TMPOPT for each pattern
    for pattern in patterns:
        regex = re.compile(pattern)
        count = sum(1 for line in TMPOPT if regex.search(line))
        hits_dict[pattern] += count  # increment if exists, or add new

    # Ensure patterns not matched at all are in CSV with 0
    for pattern in patterns:
        hits_dict.setdefault(pattern, 0)

    # Write back CSV
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Entry", "Hits"])
        for pattern, count in hits_dict.items():
            writer.writerow([pattern, count])