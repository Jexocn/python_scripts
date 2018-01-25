#encoding=utf8
import os
import sys
import subprocess
import re

ignores = ['.git']

def fnames_filter(fnames):
	for fname in ignores:
		if fname in fnames:
			fnames.remove(fname)

def gen_zipfile_name(dirname, start_id):
	while True:
		zipfname = os.path.join(dirname, "{:05d}.7z".format(start_id))
		if not os.path.exists(zipfname):
			return zipfname, start_id + 1
		start_id += 1

def zip_file(dirname, fname, id_dict):
	full_path = os.path.join(dirname, fname)
	if os.path.isfile(full_path) and full_path != self_path:
		basename, extname = os.path.splitext(fname)
		if extname != ".7z" and not zipped.has_key(full_path):
			if id_dict.has_key(dirname):
				zip_file_id = id_dict[dirname]
			else:
				zip_file_id = 0
			zip_fname, zip_file_id = gen_zipfile_name(dirname, zip_file_id)
			id_dict[dirname] = zip_file_id
			print "zip [{0}] ===> [{1}]".format(full_path, zip_fname)
			if passwd:
				r = subprocess.call(['7z', 'a', '-mhe=on', '-p{0}'.format(passwd), zip_fname, full_path])
			else:
				r = subprocess.call(['7z', 'a', '-mhe=on', zip_fname, full_path])
			if r == 0:
				print "zip [{0}] ===> [{1}] ok".format(full_path, zip_fname)
				if remove_origin:
					print "remove [{0}]".format(full_path)
					os.remove(full_path)
					print "remove [{0}] done".format(full_path)
			else:
				print "zip [{0}] --> [{1}] fail, error code is {2}".format(full_path, zip_fname, r)
		elif extname != ".7z" and remove_origin:
			print "remove [{0}]".format(full_path)
			os.remove(full_path)
			print "remove [{0}] done".format(full_path)

def zip_walk(arg, dirname, fnames):
	fnames_filter(fnames)
	fnames.sort()
	for fname in fnames:
		zip_file(dirname, fname, arg)

def make_zip_file_list(zip_info):
	lines = [re.split('\s+', line.strip()) for line in zip_info.split('\n')]
	fields_k = None
	field_names = ["Date", "Time", "Attr", "Size", "Compressed", "Name"]
	for k in xrange(0, len(lines)):
		line = lines[k]
		all_field_found = True
		for name in field_names:
			if not name in line:
				all_field_found = False
				break
		if all_field_found:
			fields_k = k
			break
	dash_begin = None
	dash_end = None
	for k in xrange(fields_k+1, len(lines)):
		line = lines[k]
		if len(line) > 0:
			all_dash = True
			for s in line:
				if not re.match('\-+$', s):
					all_dash = False
					break
			if all_dash and all_dash > 0:
				if not dash_begin:
					if 'Name' in lines[k-1]:
						dash_begin = k
				elif not dash_end:
					dash_end = k
	Name_k = None
	for k in xrange(0, len(lines[fields_k])):
		if lines[fields_k][k] == 'Name':
			Name_k = k
			break
	return [lines[k][Name_k] for k in xrange(dash_begin+1, dash_end)]

def check_file(dirname, fname, zipped):
	full_path = os.path.join(dirname, fname)
	if os.path.isfile(full_path):
		basename, extname = os.path.splitext(fname)
		if extname == ".7z":
			print "check [{0}]".format(full_path)
			if passwd:
				r = subprocess.check_output(['7z', 'l', '-p{0}'.format(passwd), full_path])
			else:
				r = subprocess.check_output(['7z', 'l', full_path])
			for fn in make_zip_file_list(r):
				zipped[os.path.join(dirname, fn)] = full_path
			print "check [{0}] done".format(full_path)	

def check_walk(arg, dirname, fnames):
	fnames_filter(fnames)
	for fname in fnames:
		check_file(dirname, fname, arg)

def zip_files(top_path):
	os.path.walk(top_path, zip_walk, {})

def check_zipped(top_path):
	zipped = {}
	os.path.walk(top_path, check_walk, zipped)
	print "----------------------------------------"
	print "zipped fiels:"
	for (k,v) in zipped.items():
		print k, "->", v
	print "----------------------------------------"
	return zipped

if __name__ == "__main__":
	self_path = os.path.abspath(sys.argv[0])
	argc = len(sys.argv)
	passwd = None
	remove_origin = False
	top_path = os.path.join(os.path.dirname(self_path))
	if argc > 1:
		passwd = sys.argv[1]
		if argc > 2:
			remove_origin = int(sys.argv[2]) == 1
			if argc > 3:
				top_path = os.path.abspath(sys.argv[3])
	print "zip files in [{0}] passwd:{1} remove_origin:{2}".format(top_path, passwd, remove_origin)
	zipped = check_zipped(top_path)
	zip_files(top_path)
