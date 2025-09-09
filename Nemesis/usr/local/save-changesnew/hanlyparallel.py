import logging
import traceback
import os
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from hanlymc import hanly
from pyfunctions import detect_copy

def logger_process(results, rout, tfile, scr="/tmp/scr", cerr="/tmp/cerr", dbopt="/usr/local/save-changesnew/recent.db", table="logs"):
	key_to_files = {
		"flag": [rout],
#		"tout": [tfile],
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

		#if "sys" in entry:
			#conn.commit()

		if "dcp" in entry:
			dcp_messages = entry["dcp"]
			if not isinstance(dcp_messages, list):
				dcp_messages = [dcp_messages]

			if dcp_messages:
				with open(rout, 'a') as file, open(tfile, 'a') as file2:
						for msg in dcp_messages:
							try:
								timestamp = msg[0]
								label = msg[1]
								ct = msg[2]
								inode = msg[3]   
								checksum = msg[5]
								result = detect_copy(label, inode, checksum, c, table)
								if result:
									print(f'Copy {timestamp} {ct} {label}', file=file)
									print(f'Copy {timestamp} {label}', file=file2)
									# print(f'System file: {msg[1]}', file=file7)

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

			if fpath == rout:
				try:
					with open(rout, "r") as rf, open(tfile, "a") as tf:
						for line in rf:
							parts = line.strip().split()
							filtered = [parts[i] for i in range(len(parts)) if i not in (3, 4)]
							tf.write(' '.join(filtered) + '\n')
				except IOError as e:
					print(f"Error copying from {rout} to {tfile}: {e}")
                              
						
def hanly_parallel(rout, tfile, parsed, checksum, cdiag, dbopt, ps, user, dbtarget, table):
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

    logger_process(all_results, rout, tfile, '/tmp/scr', '/tmp/cerr', dbopt, table)