#!/usr/bin/env python
#encoding=utf-8

#TO_DO
#优化文件以及文件夹路径处理，增加超时机制，避免长时间处理某个文件，将超时的文件记录下来

import os
import sys
import delegator
import random
import hashlib
import optparse
import shutil
import logging
import tempfile
import functools

probe_length_cmd = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {0}"
md5sum_cmd = "md5sum {0}"
ffmpeg_md5_cmd = "ffmpeg -ss {0} -t {1} -y -accurate_seek -i {2} -codec copy {3}"
string_placeholder = "_white"
current_path = os.path.dirname(os.path.abspath(__file__))
placeholder = '_out'
extensions = {".mp4", ".mov", ".avi", ".mkv"}

if __debug__:
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.DEBUG)
    handler= logging.FileHandler(os.path.join(tempfile.gettempdir(), "logged.log"))
    logger.addHandler(handler)

    def logged(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            log = "called:" + function.__name__ + "("
            log += ",".join(["{0!r}".format(a) for a in args] + 
                            ["{0!s}={1!r}".format(k, v) for k, v in kwargs.items()])
            result = exception = None
            try:
                result = function(*args, **kwargs)
                return result
            except Exception as err:
                exception = err
            finally:
                log += ((")->" + str(result)) if exception is None 
                        else "){0}:{1}".format(type(exception), exception))
                logger.debug(log)
                if exception is not None:
                    raise exception
        return wrapper
else:
    def logged(function):
        return function
        
def process_options():
    usage = """%prog [options] [path1 [path2 [... pathN]]]

    Tha paths is optional; if not given . is used."""

    parser = optparse.OptionParser(usage=usage)

    parser.add_option("-r", "--rescursive", dest="rescursive",
                        action="store_true",
                        help=("rescursive into subdirectories [default: off]"))
    parser.add_option("-t", "--tweak", dest="tweak_file",
                        action="store_true",
                        help=("do md5 tweak [default: off]"))
    parser.add_option("-H", "--hidden", dest="hidden",
                        action="store_true",
                        help=("show hidden files [default: off]"))
    parser.add_option("-c", "--clear", dest="clear_outfiles",
                        action="store_true",
                        help=("clear ffmpeg output files [default: off]"))
    parser.add_option("-m", "--move", dest="dest_dir",
                        action="store",
                        help=("move file to dest path"))
    opts, args = parser.parse_args()
    if not args:
        args = ["."]
    return opts, args


def get_filenames(opts, paths):
    if not opts.rescursive:
        filenames = []
        for path in paths:
            if os.path.isfile(path):
                filenames.append(path)
                continue
            for name in os.listdir(path):
                if not opts.hidden and name.startswith("."):
                    continue
                fullname = os.path.join(path, name)
                if fullname.startswith("./"):
                    fullname = fullname[2:]
                if os.path.isfile(fullname):
                    filenames.append(fullname)
        return filenames
    else:
        filenames = []
        for path in paths:
            for root, dirs, files in os.walk(path):
                if not opts.hidden:
                    dirs[:] = [dir for dir in dirs if not dir.startswith(".")]
                for name in files:
                    if not opts.hidden and name.startswith("."):
                        continue
                    fullname = os.path.join(root, name)
                    if fullname.startswith("./"):
                        fullname = fullname[2:]
                    filenames.append(fullname)
        return filenames


def rename_files(opts, paths):
    for path in paths:
        for parent, dirnames, filenames in os.walk(path):
            for filename in filenames:
                print filename
                os.rename(os.path.join(parent, filename), os.path.join(parent, filename.replace(' ','_')))


def add_logo(old_name):
    #print "adding_logo...\n" + old_name
    old = os.path.splitext(old_name)[0]
    ext = os.path.splitext(old_name)[1]
    if placeholder in old:
        return old_name
    out_name = old + placeholder + ext
    return out_name


def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
    for block in bytesiter:
        hasher.update(block)
    return (hasher.hexdigest() if ashexstr else hasher.digest())



def file_as_blcokiter(afile, blocksize=65536):
    with afile:
        block = afile.read(blocksize)
        while len(block) > 0:
            yield block
            block = afile.read(blocksize)


def checksum(fname):
    for item in [(fname, hash_bytestr_iter(file_as_blcokiter(open(fname, 'rb')), hashlib.md5()))]:
        print item


def probe_file(filename):
    cmd = probe_length_cmd.format(filename)
    result = delegator.run(cmd)
    if not result.return_code == 0:
        print "probe cmd is:" + cmd
        print "probe output:" + result.err
        return
    return float(result.out)


def tweakfile(filename, duration, opts, outfile):
    ss = "00:00:00" + "." + str(random.randint(1, 99))
    #print "tweaking file...\n" + outfile
    t = duration - 2
    cmd = ffmpeg_md5_cmd.format(ss, t, filename, outfile)
    #print cmd
    result = delegator.run(cmd)
    if not result.return_code == 0:
        print cmd
        print filename
        print result.err
        return 


def clear_outfiles(files, opts):
    if not files:
        print "no files to be removed..."
    for file in files:
        try:
            os.remove(file)
        except OSError as err:
            print "deleting {0} failed: {1}".format(file, err)
        else:
            continue            

def move_oldfiles(old_files, opts, path):
    dest_dir = opts.dest_dir
    if dest_dir == ".":
        dest_dir = path
    for file in old_files:
        try:
            print file
            print dest_dir
            shutil.move(file, dest_dir)
        except EnvironmentError as err:
            print "moving {0} failed with err:{1}".format(file, err)
            continue
    pass

def main():
    opts, paths = process_options()
    rename_files(opts, paths)
    filenames = get_filenames(opts, paths)
    old_files = []
    new_files = []
    for file in filenames:
        if not os.path.splitext(file)[1].lower() in extensions:
            continue
        if placeholder in file:
            continue
        old_files.append(file)
        outfile = add_logo(file)
        new_files.append(outfile)
    print old_files
    if opts.tweak_file:
        for file in old_files:
            print "{:*>70}".format('')
            print "tweaking file...."
            file_duration = probe_file(file)
            if not file_duration:
                continue
            checksum(file)
            outfile = add_logo(file)
            tweakfile(file, file_duration, opts, outfile)
            checksum(outfile)
    if opts.clear_outfiles:
        print "clear file"
        print new_files
        clear_outfiles(new_files, opts)
    if opts.dest_dir:
        print "moving files"
        path = paths[0]
        move_oldfiles(old_files, opts, path)
    #print new_files

if __name__ == "__main__":
    main()
