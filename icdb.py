# -*- coding: utf-8 -*-
"""
An incredibly basic, not very flexible database for keeping track of all
the initial conditions that I create.  This is not user friendly, but mostly
for my personal use

EXAMPLE

import icdb

# Create a new database looking at 2 base directories (and all subdirectories)

# Finds all files matching '*_settings.p'

db = icdb.database('*_settings.p', '~/simulations', \
'/home/ibackus/hyak/gscratch/vsm/ibackus/simulations')

# Query the full paths to IC files:

db.data('filename')

# Query Qmin

db.data('sigma.Qmin')

# Access the settings/information for the first simulation

sim_settings = db.data[0]

# Refresh database

db.refresh()

Created on Mon Sep 15 16:06:30 2014

@author: ibackus
"""
import numpy as np
import ICgen_settings
import os
import fnmatch

import pynbody
SimArray = pynbody.array.SimArray

class database():
    
    """
    IC database class.  Initialize with:
    
        db = icdb.database(filefilter, dir1, dir2, ...)
    
    filefilter is a string used to filter IC settings files, ie '*_settings.p'
    dir1, dir2 are base directories which are recursively searched to find
    settings files
    
    To use all and only the supplied directories, set exact_dirs=True:
    
        db = icdb.database(filefilter, dir1, dir2, ..., exact_dirs=True)
    """
    
    def __init__(self, filefilter='IC_settings.p', *directories, **kwargs):
        
        print 'Building database...'
        if len(directories) == 0:
            
            directories = ['.']
        print 'Number of base directories: ', len(directories)
        self.dirs = directories
        self.filefilter = filefilter
        self._kwargs = kwargs
        
        # keyword args defaults
        exact_dirs = False
        recursive = True
        
        # Parse keyword args
        for key, val in kwargs.iteritems():
            
            if key is 'exact_dirs':
                # Exact dirs is the flag that basically says don't search
                # recursively
                exact_dirs = val
                recursive = not exact_dirs
                
            else:
                
                raise KeyError, 'Unrecognized argument {0}'.format(key)
        
        matches = []
        
        for directory in directories:
            
            print 'Building for ', directory            
            new_matches = self._scan_dir(directory, filefilter, recursive=recursive)
            print '    Found {} files'.format(len(new_matches))
            matches += new_matches
            
            
        if not exact_dirs:
            # Remove duplicate files.  changes order, but required if directories
            # are recursively searched
            filelist = list(set(matches))
            
        else:
            
            filelist = matches
        
        datalist = []
        
        for i, fname in enumerate(filelist):
            
            a = ICgen_settings.settings()
            a.load(fname)
            a_dir = os.path.split(fname)[0]
            ICname = a.filenames.IC_file_name
            ICname = os.path.join(a_dir, ICname)
            ICname = os.path.realpath(ICname)
            
            if os.path.exists(ICname):
                
                a.dir = os.path.realpath(a_dir)
                a.ICname = ICname
                datalist.append(a)
            
        nfiles = len(datalist)
        print 'Found {} files in total'.format(nfiles)
        data = fancy_array(nfiles)
        data[:] = datalist
        self.data = data
        
    def nfiles(self):
        """
        Returns the current number of files in the database
        """
        
        return len(self.data)
    
    def _scan_dir(self, basedir='.', filefilter='*', kind='IC', recursive=True):
        """
        Recursively scan the directory basedir for files matching filefilter.
        If recursive=False, only basedir is searched
        """
        
        if kind is 'IC':
            
            matches = []
            
            if recursive:
            # Recursive search for files matching filefilter
                for root, dirnames, filenames in os.walk(basedir):
                    for filename in fnmatch.filter(filenames, filefilter):
                        fname = os.path.join(root, filename)
                        fname = os.path.realpath(fname)
                        matches.append(fname)
                    
            else:
            # Only search the basedir
                filenames = os.listdir(basedir)
                
                for filename in fnmatch.filter(filenames, filefilter):
                    
                    fname = os.path.join(basedir, filename)
                    fname = os.path.realpath(fname)
                    matches.append(fname)
                    
            return matches
                    
    def refresh(self):
        """
        Refreshes the database by re-initializing it
        """
        
        self.__init__(self.filefilter, *self.dirs, **self._kwargs)

class fancy_array(np.ndarray):
    
    def __new__(subtype, shape, buffer=None, offset=0, \
    strides=None, order=None):
        
        if not isinstance(shape, int):
            
            raise ValueError, 'Shape must be an integer.  1D arrays only'
            
        dtype = object
        
        obj = np.ndarray.__new__(subtype, shape, dtype, buffer, offset, \
        strides, order)
        
        return obj
        
    def __array_finalize__(self, obj):
        
        if obj is None: 
            
            return
            
        #self.info = getattr(obj, 'info', None)
        #self.info = obj.info
        
    def __call__(self, attr):
        
        if hasattr_nested(self[0], attr):
            
            obj = getattr_nested(self[0], attr)
            dtype = get_type(obj)
            
        else:
            
            dtype = object
            
        if dtype is SimArray:
            
            outarray = SimArray(np.zeros(self.shape), obj.units)
            
        else:
            
            outarray = np.zeros(self.shape, dtype=dtype)
        
        #outarray = np.ndarray(self.shape, dtype=object)
        #outarray = np.zeros(self.shape, dtype=object)
        
        for i, entry in enumerate(self):
            
            if hasattr_nested(entry, attr):
                
                outarray[i] = getattr_nested(entry, attr)
            
            else:
                
                outarray[i] = None
                
        return outarray
            
        
def hasattr_nested(obj, attr):
    """
    Check whether an object contains a specified (possibly nested) attribute
    
    ie:
    
    hasattr_nested(obj, 'x.y.z') will check if obj.x.y.z exists
    """
    
    parts = attr.split('.')
    
    for part in parts:
        
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            return False
    else:
        return True
        
def getattr_nested(obj, attr):
    """
    Get attribute (possibly nested) from object
    
    ie:
    
    a = getattr_nested(obj, 'x.y.z')
    
    is equivalent to a = obj.x.y.z
    """
    
    parts = attr.split('.')
    
    for part in parts:
        
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            return False
    else:
        return obj
        
def get_type(obj):
    """
    Attempts to get the type of a settings object.  These are all numbers,
    SimArrays, or strings.  Otherwise, they'll just be treated as objects
    """
    number_types = [float, int, long, complex]
    if pynbody.units.has_units(obj):
        
        return SimArray
        
    elif isinstance(obj, np.ndarray):
        
        return obj.dtype
        
    for number_type in number_types:
        
        if isinstance(obj, number_type):
        
            return number_type
        
    return object