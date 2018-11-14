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
import codecs

probe_length_cmd = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {0}"
md5sum_cmd = "md5sum {0}"
ffmpeg_md5_cmd = "ffmpeg -ss {0} -t {1} -y -accurate_seek -i {2} -codec copy {3}"
string_placeholder = "_white"
current_path = os.path.dirname(os.path.abspath(__file__))
placeholder = '_out'
extensions = {".mp4", ".mov", ".avi", ".mkv"}


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
                    print(codecs.escape_decode(bytes(fullname, 'utf-8')))                
                    fullname = codecs.escape_decode(bytes(fullname, 'utf-8'))[0].decode('utf-8')
                    print(fullname)
                    filenames.append(fullname)
        return filenames



def rename(old_file, opts):
    old = os.path.splitext(old_file)[0]
    ext = os.path.splitext(old_file)[1]
    placeholder = '_out'
    new_file = old + placeholder + ext
    try:
        #os.rename(old_file, new)
        print(old_file)
        print(new_file)
    except EnvironmentError as err:
        print('rename error: {0} {1}'.format(old_file, err))
    else:
        return new_file


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
        print(item)


def probe_file(filename):
    cmd = probe_length_cmd.format(filename)
    result = delegator.run(cmd)
    if not result.return_code == 0:
        print("probe cmd is:" + cmd)
        print("probe output:" + result.err)
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
        print(cmd)
        print(filename)
        print(result.err)
        return 


def clear_outfiles(files, opts):
    if not clear_outfiles:
        print("no files to be removed...")
    for file in files:
        try:
            os.remove(file)
        except OSError as err:
            print("deleting {0} failed: {1}".format(file, err))
        else:
            continue            

def main():
    opts, paths = process_options()
    filenames = get_filenames(opts, paths)
    print(filenames)
    new_files = []
    for file in filenames:
        print(file)
        if not os.path.splitext(file)[1] in extensions:
            continue
        if placeholder in file:
            continue
        file_duration = probe_file(file)
        if not file_duration:
            continue
        outfile = add_logo(file)
        new_files.append(outfile)
        if opts.tweak_file:
            print("{:*>70}".format(''))
            checksum(file)
            print("tweaking file...")
            tweakfile(file, file_duration, opts, outfile)
            #print new_file
            checksum(outfile)
    if opts.clear_outfiles:
        print("clear file")
        print(new_files)
        clear_outfiles(new_files, opts)
    #print new_files

if __name__ == "__main__":
    main()
