import copy
import glob
import hashlib
import os
import sys
import time
import types

files = {}
hashes = {}
dirs = {}
pdirs = {}
keys = []
circular = []
filters = []

#
# Scan and build

def recurse_path(path):
	global files

	for file in glob.iglob(path + "/*"):
		if os.path.isdir(file):
			recurse_path(file)
		else:
			size = os.stat(file).st_size
			if size in files:
				files[size].append(file)
			else:
				files[size] = [file]

def hash_files():
	global files
	global hashes
	global circular
	
	hashes = {}
	for size in files:
		if len(files[size]) > 1:
			for i in files[size]:
				m = hashlib.md5()
				m.update(open(i, "rb").read())
				s = m.hexdigest()
				
				if s in hashes:
					hashes[s].append(i)
				else:
					hashes[s] = [i]

	circular = []
	for hash in hashes:
		dnames = []
		for f in hashes[hash]:
			dname = os.path.dirname(f)
			if not dname in dnames:
				dnames.append(dname)
			else:
				circular.append(f)

	files = {}

def dir_scan():
	global hashes
	global dirs
	global pdirs

	dirs = {}
	for hash in hashes:
		if len(hashes[hash]) > 1:
			for i in hashes[hash]:
				d,f = os.path.split(i)
				if d in dirs:
					dirs[d]["dups"].append(i + "##" + hash)
					dirs[d]["size"] += os.stat(i).st_size
				else:
					dirs[d] = {}
					dirs[d]["dups"] = [i + "##" + hash]
					dirs[d]["total"] = len(glob.glob(d + "/*.*"))
					dirs[d]["size"] = os.stat(i).st_size

	pdirs = {}
	for d in dirs:
		diff = dirs[d]["total"] - len(dirs[d]["dups"])
		size = dirs[d]["size"]
		if size in pdirs:
			pdirs[size].append(d)
		else:
			pdirs[size] = [d]

def process(inp_dirs):
	for i in inp_dirs:
		recurse_path(i)
	hash_files()
	dir_scan()

#
# Actions

def move_dir(d):
	global dirs
	global circular
	
	md = os.path.splitdrive(d)[1]
	if md[0] in ["/", "\\"]:
		md = md[1:]
	md = os.path.join("dup_backup/", md)
	
	try:
		os.makedirs(md)
	except:
		pass
		
	if not os.path.exists(md):
		print "Unable to write to %s" % os.getcwd()

	for f in dirs[d]["dups"]:
		file, hash = f.split("##", 1)
		if file in circular:
			continue
		os.rename(file, os.path.join(md, os.path.basename(file)))
		
	if not len(glob.glob(os.path.join(d, "*.*"))):
		time.sleep(1)
		os.rmdir(d)
	
	del_dir(d)

def del_dir(d):
	global pdirs
	
	for size in sorted(pdirs.keys(), reverse=True):
		if d in pdirs[size]:
			pdirs[size].remove(d)
			break

#
# I/O

def menu():
	global keys
	global filters
	
	print_dirs()
	while True:
		inp = raw_input(">> ").strip()
		if inp == "":
			continue
		
		spl = inp.split(" ", 1)
		if len(spl) == 1:
			com = inp.lower()

			if com == "quit"[:len(com)] or com == "exit"[:len(com)]:
				break
			elif com == "list"[:len(com)]:
				print_dirs()
			elif com == "reload"[:len(com)]:
				process(sys.argv[1:])
				print_dirs()
			elif com == "clear"[:len(com)]:
				if "win" in sys.platform:
					os.system("cls")
				else:
					os.system("clear")
			elif com == "filter"[:len(com)]:
				print "Filters"
				for filt in sorted(filters):
					print "  " + filt
			else:
				try:
					key = int(com)
					d = keys[key-1]
					print_dups(d)
				except:
					pass
			
		elif len(spl) == 2:
			com = spl[0].lower()
			
			if com == "filter"[:len(com)]:
				if spl[1] in filters:
					filters.remove(spl[1])
				else:
					filters.append(spl[1])
					filters = sorted(filters, reverse=True)
				print_dirs()
			else:
				if spl[1] == "ALL":
					spl[1] = " ".join([("%d" % (i+1)) for i in range(len(keys))])
					
				try:
					ikeys = spl[1].split(" ")
					for key in sorted(ikeys, reverse=True):
						key = int(key)
						d = keys[key-1]
						
						if com == "open"[:len(com)]:
							os.startfile(d)
						elif com == "move"[:len(com)]:
							move_dir(d)
						elif com == "dups"[:len(com)]:
							print_dups(d)
						elif com == "nondups"[:len(com)]:
							print_non_dups(d)
					
					if com == "move"[:len(com)]:
						print_dirs()
				except:
					print "Bad syntax"

def print_dir_header(d):
	global dirs
	
	dups = len(dirs[d]["dups"])
	total = dirs[d]["total"]
	size = dirs[d]["size"]
	
	print "%.2f MB  %s" % (float(size) / 1024 / 1024, d),
	if dups == total:
		print " (*)"
	else:
		print " (%d)" % dups

def print_dirs():
	global dirs
	global pdirs
	global keys
	global filters

	print "Directories with duplicates"
	keys = []
	tsize = 0
	skip = False
	for size in sorted(pdirs.keys(), reverse=True):
		for d in sorted(pdirs[size]):
			for filt in filters:
				if filt == d[:len(filt)]:
					skip = True
					break
			if skip == True:
				skip = False
				continue
				
			print "%d:" % (len(keys)+1),
			print_dir_header(d)
			keys.append(d)
			tsize += dirs[d]["size"]
	print "Total duplicates: %0.2f MB" % (float(tsize) / 1024 / 1024)

def print_dups(d):
	global dirs
	global circular

	print_dir_header(d)
	for f in sorted(dirs[d]["dups"]):
		file, hash = f.split("##", 1)
		if file in circular:
			continue

		dups = copy.deepcopy(hashes[hash])
		dups.remove(file)
		print "  %s => %s" % (os.path.basename(file), " ".join(dups))

def print_non_dups(d):
	global dirs
	global circular

	print_dir_header(d)
	all = glob.glob(os.path.join(d, "*.*"))
	for f in sorted(dirs[d]["dups"]):
		file, hash = f.split("##", 1)
		if file in circular:
			continue
			
		try:
			all.remove(file)
		except:
			pass

	for f in all:
		print "  %s" % os.path.basename(f)

if __name__ == "__main__":
	process(sys.argv[1:])
	menu()