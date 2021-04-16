# -*- coding: utf-8 -*-

import time
from functools import wraps


import cProfile, pstats

import os
import csv

import pandas as pd

"""
Quick guide to profiling: functions of which profiling is of interest have been identified via a first visually comprehesive profiling using pyinstrument
After identification, the profiler decorator has been added above their definitions.
Run pyinstrument in the terminal: pyinstrument -r html testscript.py
"""

def time_this(func):
    """Time measurer decorator"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        res = func(*args, **kwargs)
        end = time.perf_counter()
        print(f'{func.__module__}.{func.__name__} : {end - start}')
        output_file_name = os.path.join(func.__name__+'_time.csv')
        with open(output_file_name, 'a') as csvfile: # 'a' if decorated function called successively i.e. as comparison, 'w' if unique call
            fieldnames = ['Module.Function', 'Time']
            writer = csv.DictWriter(csvfile, delimiter=",", fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({'Module.Function':f'{func.__module__}.{func.__name__}' , 'Time':end-start})

        return res
    return wrapper


def profile_this(output_file=None, sort_by='cumulative', lines_to_print=None, strip_dirs=False):
    """A time profiler decorator.
    """

    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _output_file = output_file or os.path.join('benchmark'+ '/' + func.__name__ + '_pr' + '.csv')
            pr = cProfile.Profile()
            pr.enable()
            retval = func(*args, **kwargs)
            pr.disable()
            pr.dump_stats(_output_file)
            
            with open(_output_file, 'w') as f:
                ps = pstats.Stats(pr, stream=f)
                if strip_dirs:
                    ps.strip_dirs()
                if isinstance(sort_by, (tuple, list)):
                    ps.sort_stats(*sort_by)
                else:
                    ps.sort_stats(sort_by)
                ps.print_stats(lines_to_print)
            return retval

        return wrapper

    return inner


def compare_profile(prof1, prof2):
    """ Compares execution time profiling of 2 cProfile csv profile outputs
    Inputs: 2 csv profiles
    Output: profile differences from prof1 to prof2
    """
    df1=create_profile_dictionary(prof1)
    df2=create_profile_dictionary(prof2)
    #Computes difference
    diff=df2-df1
    #Ignores non-matching functions
    diff.dropna(inplace=True)    
    #Sorts according to largest absolute difference
    diff['absolute difference']=abs(diff.cumtime)
    diff.sort_values(['absolute difference'], ascending=False, inplace=True)
    return diff
    

def create_profile_dictionary(prof_path):
    """ Reads profiling csv and extract manipulable dictionary
    Input: csv profile of a script or function
    Output: profiling data converted into a manipulable DataFrame
    """
    colnames=['ncalls','tottime','percall','cumtime','perprimcall','filename:lineno(function)']
    #Reads profiling csv row by row and ignores built-in methods
    with open(prof_path) as csv_prof:
        prof_df = pd.read_csv(csv_prof, quotechar='{', names=colnames, sep='\s+', error_bad_lines=False, header=2, engine="python")
    filename_function_split = prof_df['filename:lineno(function)'].str.split("(", expand=True)
    filename_function_split.rename(columns={0:'filename:lineno', 1:'function'}, inplace=True)
    filename_function_split['function']=filename_function_split['function'].str.split(")", expand=True)
    prof_df = pd.merge(prof_df, filename_function_split, left_index=True, right_index=True)
    prof_df.drop(['filename:lineno(function)'], axis=1, inplace=True)
    prof_df.set_index(['filename:lineno','function'], inplace=True)
    prof_df=prof_df[~prof_df.ncalls.str.contains("/")] #ignores recursive functions as it concerns built-in ones, but could be handled better
    prof_df=prof_df.astype({'ncalls': 'int32'})
    prof_df.drop(prof_df[prof_df.cumtime<0.001].index, inplace=True) #ignores functions of negligible execution times
    return prof_df
