#!/usr/bin/env python

# Copyright 2011 Peter Odding <peter@peterodding.com>
# This program is licensed under the MIT license.
#
# This Python script can be used by the notes.vim plug-in to perform fast
# keyword searches in the user's notes. It has two advantages over just using
# Vim's internal :vimgrep command to search all of the user's notes:
# 
#  - Very large notes don't slow searching down so much;
#  - Hundreds of notes can be searched in less than a second.
# 
# For more information about the Vim plug-in see http://peterodding.com/code/vim/notes/.

# Standard library modules.
import fnmatch
import getopt
import os
import pickle
import re
import sys

class NotesIndex:

  def __init__(self):
    ''' Entry point to the notes search. '''
    keywords = self.parse_args()
    self.load_index()
    self.update_index()
    if self.dirty:
      self.save_index()
    matches = self.search_index(keywords)
    print '\n'.join(sorted(matches))

  def parse_args(self):
    ''' Parse the command line arguments. '''
    try:
      opts, keywords = getopt.getopt(sys.argv[1:], 'd:n:e:h',
          ['database=', 'notes=', 'encoding=', 'help'])
    except getopt.GetoptError, error:
      print str(error)
      self.usage()
      sys.exit(2)
    # Define the command line option defaults.
    self.database_file = '~/.vim/misc/notes/index.pickle'
    self.user_directory = '~/.vim/misc/notes/user/'
    self.character_encoding = 'UTF-8'
    # Map command line options to variables.
    for opt, arg in opts:
      if opt in ('-d', '--database'):
        self.database_file = arg
      elif opt in ('-n', '--notes'):
        self.user_directory = arg
      elif opt in ('-e', '--encoding'):
        self.character_encoding = arg
      elif opt in ('-h', '--help'):
        self.usage()
        sys.exit(0)
      else:
        assert False, "Unhandled option"
    # Canonicalize pathnames, check validity.
    self.database_file = self.munge_path(self.database_file)
    self.user_directory = self.munge_path(self.user_directory)
    if not os.path.isdir(self.user_directory):
      sys.stderr.write("Notes directory %s doesn't exist!\n" % self.user_directory)
      sys.exit(1)
    # Return tokenized keyword arguments.
    return self.tokenize(' '.join(keywords))

  def load_index(self):
    ''' Load the keyword index or start with an empty one. '''
    try:
      with open(self.database_file) as handle:
        self.index = pickle.load(handle)
        assert self.index['version'] >= 1
        self.first_use = False
        self.dirty = False
    except:
      self.first_use = True
      self.dirty = True
      self.index = {'keywords': {}, 'files': {}, 'version': 1}

  def save_index(self):
    ''' Save the keyword index to disk. '''
    with open(self.database_file, 'w') as handle:
      pickle.dump(self.index, handle)

  def update_index(self):
    ''' Update the keyword index by scanning the notes directory. '''
    # First we find the filenames and last modified times of the notes on disk.
    notes_on_disk = {}
    for filename in os.listdir(self.user_directory):
      if filename != '.swp' and not fnmatch.fnmatch(filename, '.*.s??'): # (Vim swap files are ignored)
        abspath = os.path.join(self.user_directory, filename)
        if os.path.isfile(abspath):
          notes_on_disk[abspath] = os.path.getmtime(abspath)
    # Then we either scan the whole bunch or be a bit more subtle.
    if self.first_use:
      for filename, last_modified in notes_on_disk.iteritems():
        self.add_note(filename, last_modified)
    else:
      # Check for updated and/or deleted notes since the last run.
      for filename, last_modified_in_db in self.index['files'].iteritems():
        if filename not in notes_on_disk:
          # Forget a deleted note.
          self.delete_note(filename)
        else:
          # Check whether previously seen note has changed?
          last_modified_on_disk = notes_on_disk[filename]
          if last_modified_on_disk > last_modified_in_db:
            self.delete_note(filename)
            self.add_note(filename, last_modified_on_disk)

  def add_note(self, filename, last_modified):
    ''' Add a note to the index (assumes the note is not already indexed). '''
    sys.stderr.write("Scanning %s ..\n" % filename)
    self.index['files'][filename] = last_modified
    with open(filename) as handle:
      for kw in self.tokenize(handle.read()):
        if kw not in self.index['keywords']:
          self.index['keywords'][kw] = [filename]
        else:
          self.index['keywords'][kw].append(filename)
    self.dirty = True

  def delete_note(self, filename):
    ''' Remove a note from the index. '''
    del self.index['files'][filename]
    for kw in self.index['keywords']:
      filter(lambda x: x != filename, self.index['keywords'][kw])
    self.dirty = True

  def search_index(self, keywords):
    ''' Return names of files containing all of the given keywords. '''
    matches = None
    for kw in keywords:
      filenames = self.index['keywords'].get(kw, [])
      if matches is None:
        matches = set(filenames)
      else:
        matches &= set(filenames)
    return list(matches) if matches else []

  def tokenize(self, text):
    ''' Tokenize a string into a list of normalized, unique keywords. '''
    words = set()
    text = text.decode(self.character_encoding, 'ignore')
    for word in re.findall(r'\w+', text.lower(), re.UNICODE):
      word = word.strip()
      if word != '' and not word.isspace():
        words.add(word)
    return words

  def munge_path(self, path):
    ''' Canonicalize user-defined path, making it absolute. '''
    return os.path.abspath(os.path.expanduser(path))

  def usage(self):
    print '''
search-notes [OPTIONS] KEYWORD...

Search a directory of plain text files using a full text index,
updated automatically during each invocation of the program.

Valid options include:

  -d, --database=FILE  set path to keywords index file
  -n, --notes=DIR      set directory with user notes
  -e, --encoding=NAME  set character encoding of notes
  -h, --help           show this message and exit

For more information see http://peterodding.com/code/vim/notes/
'''.strip()

if __name__ == '__main__':
  NotesIndex()

# vim: ts=2 sw=2 et
