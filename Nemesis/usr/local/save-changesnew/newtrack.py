#  Ctime > mtime watchdog for bypassing 1 of 2 loops  09/25/2025 

import os
import sys
import time
from rntchangesfunctions import sbwr
from fsearch import process_lines
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import re


LCLMODULENAME=sys.argv[1]
log_file ="/tmp/file_creation_log.txt"
CACHE_F="/tmp/ctimecache" 


def should_exclude(file_path):
    exclude_patterns = sbwr(LCLMODULENAME)
    for pat in exclude_patterns:
        if pat and pat in file_path:
            return True
    return False

ignore_ext = re.compile(r"\.(tmp|swp|bak|part|crdownload|partial|lock)$")

paths_to_watch = []
try:
    for d in os.listdir("/mnt/live/memory/changes"):
        full_path = os.path.join("/mnt/live/memory/changes", d)
        if os.path.isdir(full_path):
            paths_to_watch.append(full_path)
except Exception as e:
    print(f"Error listing directories: {e}")

# Event handler
class MyHandler(FileSystemEventHandler):
    def __init__(self, CACHE_F, CSZE, checksum=True, type="ctime"):
        self.CACHE_F = CACHE_F
        self.CSZE = CSZE
        self.checksum = checksum
        self.type = type

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        try:
            if ignore_ext.search(file_path):
                return
            file_path = event.src_path
            if should_exclude(file_path):
                return
            file_path = event.src_path
            # Build line for process_line
            stat_info = os.stat(file_path)
            mod_time = str(int(stat_info.st_mtime))
            access_time = str(int(stat_info.st_atime))
            change_time = str(int(stat_info.st_ctime))
            inode = str(stat_info.st_ino)
            size = str(stat_info.st_size)
            user = str(stat_info.st_uid)
            group = str(stat_info.st_gid)
            mode = oct(stat_info.st_mode)[-3:]
            
            line = f"{mod_time} {access_time} {change_time} {inode} {size} {user} {group} {mode} {file_path}"

            process_file(file_path)
            sortcomplete, complete = process_lines(
                [line],
                self.checksum,
                self.type,
                self.CACHE_F,
                self.CSZE
            )

            if sortcomplete:
                with open(log_file, 'w') as f:
                    for entry in sortcomplete:
                        f.write(str(entry) + '\n')  # or format nicely

        except FileNotFoundError:
            print(f"File disappeared before processing: {file_path}")
        except PermissionError:
            print(f"No permission to access: {file_path}")
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")


def process_file(path):
    try:
        stat_info = os.stat(path)
        # Process file ------------>
        print(f"Processing: {path}, size: {stat_info.st_size}")
    except Exception as e:
        print(f"Error statting {path}: {e}")

# Start observer
observer = Observer()
for path in paths_to_watch:
    try:
        observer.schedule(MyHandler(), path, recursive=True)
    except Exception as e:
        print(f"Failed to schedule watcher for {path}: {e}")
observer.start()
try:
    # Run for a fixed time (seconds)
    time_to_run = 3600 
    start_time = time.time()
    while time.time() - start_time < time_to_run:
        time.sleep(1)
except Exception as e:
    print(f"Failed to start observer: {e}")
    sys.exit(1)
finally:
    observer.stop()
    observer.join()