import logging
import traceback
import os
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from hanlymc import hanly
from pyfunctions import detect_copy
															# tfile
def logger_process(results, rout, scr="/tmp/scr", cerr="/tmp/cerr", dbopt="/usr/local/save-changesnew/recent.db", table="logs"):
	key_to_files = {
		"flag": [rout],
		"cerr": [cerr],
		"scr": [scr],
	}
	conn = sqlite3.connect(dbopt)

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
						if fpath is rout:
							rout.extend(messages)
						else:
							file_messages.setdefault(fpath, []).extend(messages)

		
			if "dcp" in entry:
				dcp_messages = entry["dcp"]
				if not isinstance(dcp_messages, list):
					dcp_messages = [dcp_messages]

				if dcp_messages:

					for msg in dcp_messages:
						try:
							timestamp = msg[0]
							label = msg[1]
							ct = msg[2]
							#inode = msg[3]   
							checksum = msg[5]
							result = detect_copy(label, checksum, c, table)
							if result:
								rout.append(f'Copy {timestamp} {ct} {label}')


						except Exception as e:
							print(f"Error updating DB for sys entry '{msg}': {e}")
						
						
	for fpath, messages in file_messages.items():
		if messages:
			try:
				if fpath is rout:
					rout.extend(str(msg) for msg in messages)
				else:
					with open(fpath, "a") as f:
						f.write('\n'.join(str(msg) for msg in messages) + '\n')

			except IOError as e:
				print(f"Error logger to {fpath}: as {e}")



def hanly_parallel(rout, parsed, checksum, cdiag, dbopt, ps, user, dbtarget, table):
    max_workers = min(16, os.cpu_count() or 1, len(parsed) if parsed else 1)
    all_results = []

    if not parsed:
        logger_process([], rout)
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

    logger_process(all_results, rout, '/tmp/scr', '/tmp/cerr', dbopt, table)