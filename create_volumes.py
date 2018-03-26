#!/usr/bin/python
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

def get_file_size(path):
	return os.path.getsize(path)

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

def check_and_cut_file(dirname, fname, arg):
	# check if 7z file
	full_path = os.path.join(dirname, fname)
	if os.path.isfile(full_path) and full_path != self_path:
		basename, extname = os.path.splitext(full_path)
		if extname == ".7z" and get_file_size(full_path) > bytes_of_volume_size:
			print "cut [{0}]".format(full_path)
			if passwd:
				r = subprocess.check_output(['7z', 'l', '-p{0}'.format(passwd), full_path])
			else:
				r = subprocess.check_output(['7z', 'l', full_path])
			zipped_files = make_zip_file_list(r)
			zipped_files_full_fn = [os.path.join(dirname, fn) for fn in zipped_files]
			for full_fn in zipped_files_full_fn:
				if os.path.exists(full_fn):
					os.remove(full_fn)
			cmds = ['7z', 'x', '-mhe=on', '-o{0}'.format(dirname)]
			if passwd:
				cmds.append('-p{0}'.format(passwd))
			cmds.append(full_path)
			r = subprocess.call(cmds)
			if r == 0:
				print "unzip [{0}] ok".format(full_path)
				os.rename(full_path, full_path+'.bak')
				cmds = ['7z', 'a', '-mhe=on', '-v{0}'.format(volume_size)]
				if passwd:
					cmds.append('-p{0}'.format(passwd))
				cmds.append(full_path)
				cmds.extend(zipped_files_full_fn)
				r = subprocess.call(cmds)
				if r == 0:
					print "cut zip [{0}] ok".format(full_path)
					os.remove(full_path+'.bak')
				else:
					print "cut zip [{0}], error code is {2}".format(full_path, r)
					os.rename(full_path+'.bak', full_path)
				for fn in zipped_files:
					full_fn = os.path.join(dirname, fn)
					if os.path.exists(full_fn):
						os.remove(full_fn)
			else:
				print "unzip [{0}], error code is {2}".format(full_path, r)


def cut_walk(arg, dirname, fnames):
	fnames_filter(fnames)
	for fname in fnames:
		check_and_cut_file(dirname, fname, arg)


def cut(top_path):
	os.path.walk(top_path, cut_walk, None)

def get_bytes_volume_size(v):
	r = re.match("(\d+)([bkmg])$", v)
	n, u = r.groups()
	n = int(n)
	if u == 'b':
		return n
	if u == 'k':
		return n*1024
	if u == 'm':
		return n*1024*1024
	return n*1024*1024*1024

if __name__ == "__main__":
	self_path = os.path.abspath(sys.argv[0])
	argc = len(sys.argv)
	passwd = None
	volume_size = '4g'
	bytes_of_volume_size = 4*1024*1024*1024
	top_path = os.path.join(os.path.dirname(self_path))
	if argc > 1:
		passwd = sys.argv[1]
		if passwd == '':
			passwd = None
	if argc > 2 and sys.argv[2] != '':
		top_path = os.path.abspath(sys.argv[2])
	if argc > 3:
		volume_size = sys.argv[3]
		assert re.match("\d+[bkmg]$", volume_size)
		bytes_of_volume_size = get_bytes_volume_size(volume_size)
	print "cut 7z files in [{0}] passwd:{1}".format(top_path, passwd)
	cut(top_path)

	