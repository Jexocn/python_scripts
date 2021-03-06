#!/usr/bin/python
#encoding=utf8
import os
import sys
import subprocess
import re
import glob

ignores = ['.git']

def fnames_filter(fnames):
	for fname in ignores:
		if fname in fnames:
			fnames.remove(fname)

def gen_zipfile_name(dirname, start_id):
	while True:
		zipfname = os.path.join(dirname, "{:05d}.7z".format(start_id))
		if not os.path.exists(zipfname) and len(glob.glob("{0}.[0-9][0-9]*".format(zipfname))) == 0:
			return zipfname, start_id + 1
		start_id += 1

def zip_file(dirname, fname, id_dict):
	full_path = os.path.join(dirname, fname)
	if os.path.isfile(full_path) and full_path != self_path:
		r = re.search("\.7z(\.\d+)?$", fname)
		if not r and not zipped.has_key(full_path):
			basename, extname = os.path.splitext(full_path)
			if basename2zip.has_key(basename):
				zip_fname = basename2zip[basename]
			else:
				if id_dict.has_key(dirname):
					zip_file_id = id_dict[dirname]
				else:
					zip_file_id = 0
				zip_fname, zip_file_id = gen_zipfile_name(dirname, zip_file_id)
				id_dict[dirname] = zip_file_id
			print "zip [{0}] ===> [{1}]".format(full_path, zip_fname)
			cmds = ['7z', 'a', '-mhe=on']
			if volume_size:
				cmds.append('-v{0}'.format(volume_size))
			if passwd:
				cmds.append('-p{0}'.format(passwd))
			cmds.extend([zip_fname, full_path])
			r = subprocess.call(cmds)
			if r == 0:
				print "zip [{0}] ===> [{1}] ok".format(full_path, zip_fname)
				basename2zip[basename] = zip_fname
				if remove_origin:
					print "remove [{0}]".format(full_path)
					os.remove(full_path)
					print "remove [{0}] done".format(full_path)
			else:
				print "zip [{0}] --> [{1}] fail, error code is {2}".format(full_path, zip_fname, r)
		elif not r and remove_origin:
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
		if re.search("\.7z(\.0*1)?$", fname):
			print "check [{0}]".format(full_path)
			if passwd:
				r = subprocess.check_output(['7z', 'l', '-p{0}'.format(passwd), full_path])
			else:
				r = subprocess.check_output(['7z', 'l', full_path])
			for fn in make_zip_file_list(r):
				full_fn = os.path.join(dirname, fn)
				base_fn, ext_fn = os.path.splitext(full_fn)
				zipped[full_fn] = full_path
				basename2zip[base_fn] = full_path
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
	print "zipped:"
	for (k,v) in zipped.items():
		print k, "->", v
	print "basename2zip:"
	for (k,v) in basename2zip.items():
		print k, "->", v
	print "----------------------------------------"
	return zipped

if __name__ == "__main__":
	self_path = os.path.abspath(sys.argv[0])
	argc = len(sys.argv)
	passwd = None
	remove_origin = False
	volume_size = None
	top_path = os.path.join(os.path.dirname(self_path))
	if argc > 1 and len(sys.argv[1]) > 0:
		passwd = sys.argv[1]
	if argc > 2:
		remove_origin = int(sys.argv[2]) == 1
	if argc > 3 and len(sys.argv[3]) > 0:
		top_path = os.path.abspath(sys.argv[3])
	if argc > 4:
		volume_size = sys.argv[4]
		assert re.match("\d+[bkmg]$", volume_size)
	print "zip files in [{0}] passwd:{1} remove_origin:{2} volume_size:{3}".format(top_path, passwd, remove_origin, volume_size)
	basename2zip = {}
	zipped = check_zipped(top_path)
	zip_files(top_path)
