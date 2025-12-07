import traceback																												#11/28/2025
import os
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from hanlymc import hanly
from pyfunctions import detect_copy
from pyfunctions import increment_f
															# tfile
def logger_process(results,  sys_records, rout, scr="/tmp/scr", cerr="/tmp/cerr", dbopt="/usr/local/save-changesnew/recent.db", ps=False):

	crecord = False

	key_to_files = {
		"flag": [rout],
		"cerr": [cerr],
		"scr": [scr],
	}


	with sqlite3.connect(dbopt) as conn:
		c = conn.cursor()

		file_messages = {}
		for entry in results:
			for key, files in key_to_files.items():
				if key in entry:
					messages = entry[key]
					if not isinstance(messages, list):
						messages = [messages]
					for fpath in files:
						if isinstance(fpath, list):  # rout was a file in early design but now is a list. appended to it
							fpath.extend(messages)
						else:
							file_messages.setdefault(fpath, []).extend(messages)

			# check for copies from known files
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
							inode = msg[3]   
							checksum = msg[5]
							result = detect_copy(label, inode, checksum, c, ps)  # detect_copy # def detect_copy(filename, inode, checksum,  sys_table, cursor, ps):
							if result:
								rout.append(f'Copy {timestamp} {ct} {label}')


						except Exception as e:
							print(f"Error updating DB for sys entry '{msg}': {e}")

			
			if "sys" in entry:
				crecord = True

				
		# Update the counts once in sys table
		if crecord:
			try:
				increment_f(conn, c, sys_records)
			except Exception as e:
				print(f"Failed to update sys table in hanlyparallel as: {e}")			
						
	for fpath, messages in file_messages.items():
		if messages:
			try:
				with open(fpath, "a") as f:
					f.write('\n'.join(str(msg) for msg in messages) + '\n')

			except IOError as e:
				print(f"Error logger to {fpath}: as {e}")
			except Exception as e:
				print(f"Unexpected error to {fpath} logger_process: {e} : {type(e).__name__}")

 # rout, parsed, checksum, cdiag, dbopt, ps, user, dbtarget)
def hanly_parallel(rout, parsed, checksum, cdiag, dbopt, ps, user, dbtarget):

	all_results = []
	batch_incr = []

	if not parsed or len(parsed) == 0:
		return
	
	if len(parsed) < 40:
		all_results, batch_incr = hanly(parsed, checksum, cdiag, dbopt, ps, user, dbtarget)
	else:
		max_workers = min(8, os.cpu_count() or 1, len(parsed) if parsed else 1)
		chunk_size = max(1, (len(parsed) + max_workers - 1) // max_workers)
		chunks = [parsed[i:i + chunk_size] for i in range(0, len(parsed), chunk_size)]


		with ProcessPoolExecutor(max_workers=max_workers) as executor:
			futures = [
				executor.submit(
					hanly, chunk, checksum, cdiag, dbopt, ps, user, dbtarget
				)
				for chunk in chunks
			]
			for future in as_completed(futures):
				try: 
					results, sys_records = future.result()
					if results:
						all_results.extend(results)
					if sys_records:
						batch_incr.extend(sys_records)
				except Exception as e:
					print(f"Worker error from hanly multiprocessing: {type(e).__name__} {e} \n {traceback.format_exc()}")

			# for future in futures:       original
			# 	try:
			# 		all_results.extend(future.result())
			# 	except Exception as e:
			# 		print(f"Worker error from hanly multiprocessing: {type(e).__name__} {e} \n {traceback.format_exc()}")

	logger_process(all_results, batch_incr, rout, '/tmp/scr', '/tmp/cerr', dbopt, ps)