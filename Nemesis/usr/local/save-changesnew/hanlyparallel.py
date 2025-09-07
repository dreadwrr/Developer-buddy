import logging
import traceback
import os
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from hanlymc import hanly
from pyfunctions import increment_fname

def logger_process(results, rout, tfile, scr="/tmp/scr", cerr="/tmp/cerr", dbopt="/usr/local/save-changesnew/recent.db"):
	key_to_files = {
		"flag": [rout, tfile],
		"cerr": [cerr],
		"scr": [scr],
	}
	conn = sqlite3.connect(dbopt)

	#with open('/tmp/logger', 'a') as file7:
	with conn:
		c = conn.cursor()

		file_messages = {}
		for entry in results:
			for key, files in key_to_files.items():
				if key in entry:
					messages = entry[key]
					if not isinstance(messages, list):
						messages = [messages]
					for fpath in files:
						file_messages.setdefault(fpath, []).extend(messages)

			if "sys" in entry:

				sys_messages = entry["sys"]
				if not isinstance(sys_messages, list):
					sys_messages = [sys_messages]

				for msg in sys_messages:

					try:
						increment_fname(conn, c, msg)
					#	print(f'System file: {msg[1]}', file=file7)
					except Exception as e:
						print(f"Error updating DB for sys entry '{msg}': {e}")
						
	for fpath, messages in file_messages.items():
		if messages:
			try:

				with open(fpath, "a") as f:
					f.write('\n'.join(str(msg) for msg in messages) + '\n')
					#file7.write('\n'.join(str(msg) for msg in messages) + '\n')
			except IOError as e:
				print(f"Error logger to {fpath}: as {e}")
                              
						
def hanly_parallel(rout, tfile, parsed, checksum, cdiag, dbopt, ps, user, dbtarget):
    max_workers = min(16, os.cpu_count() or 1, len(parsed) if parsed else 1)
    all_results = []

    if not parsed:
        logger_process([], rout, tfile)
        return

    chunk_size = max(1, (len(parsed) + max_workers - 1) // max_workers)
    chunks = [parsed[i:i + chunk_size] for i in range(0, len(parsed), chunk_size)]


    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                hanly, chunk, checksum, cdiag, dbopt, ps, user, dbtarget
            )
            for chunk in chunks
        ]

        for future in futures:    
            try:
                all_results.extend(future.result())
            except Exception as e:
                logging.error("Worker error: %s\n%s", e, traceback.format_exc())

    logger_process(all_results, rout, tfile, '/tmp/scr', '/tmp/cerr', dbopt)