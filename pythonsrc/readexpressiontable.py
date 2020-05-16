#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 10:13:47 2020

@author: Lab
"""
from ftplib import FTP
from functools import partial
from collections import ChainMap
import os, tarfile, aiohttp, asyncio, json, tempfile, gzip, re, pandas as pd


ACCEPTED_SUFFIXES = "xlsx", "tsv", r"count\.txt"
SUFFIX_REGEX = fr"\.({'|'.join(ACCEPTED_SUFFIXES)})(\.gz)?$"


def data_table_from_file(self, filename):
    final_file_name = filename.split('/')[-1]
    print(self.cache_location / final_file_name)
    if not os.path.exists(self.cache_location / final_file_name):
        ftp = FTP('ftp.ncbi.nlm.nih.gov')
        ftp.login()
        path = filename[len('ftp://ftp.ncbi.nlm.nih.gov/'):]
        print('downloading', path)
        with open(self.cache_location / final_file_name, 'wb+') as f:
            ftp.retrbinary(f'RETR {path}', f.write)
        ftp.close()
    file_name_dict = {
        'GSE85728_RAW.tar': read_gse85728,
        'GSE140851_RAW.tar': read_gse140851,
    }
    if final_file_name in file_name_dict :
        return file_name_dict[final_file_name](self, final_file_name)
    else:
        with open(self.cache_location / final_file_name, 'rb') as zipfile:
            zipfile.seek(0)
            if filename.endswith('.gz'):
                readfile = gzip.open(zipfile, 'rt', encoding="utf-8")
                filename = filename[:-3]
            else:
                readfile = zipfile
            readfile.seek(0)
            data_table = {
                        '.xlsx': pd.read_excel,
                        '.tsv': pd.read_table,
                        '.csv': pd.read_csv,
                        '.txt': pd.read_table,
                        '.count.txt': partial(pd.read_table, names=("id", "value"))
                        }[
                        re.search(r'\.[\w.]+$', filename).group()
                        ](readfile)
            filename = filename
            readfile.close()
        return data_table

def read_gse85728(self, filename):
    series_list = []
    tar = tarfile.open(self.cache_location / filename)
    for member in tar.getmembers():
            f = tar.extractfile(member)
            sample = re.match('^[^.]+', member.name).group(0)
            if int(sample[3:10]) <= 2284991:
                continue
            readfile = gzip.open(f, 'rt', encoding="utf-8")
            df = pd.read_table(readfile)
            df.set_index('Gene_id', inplace=True)
            df.rename(columns = {list(df)[-1]:sample}, inplace=True)
            series_list.append(df)
    tar.close()
    ll = series_list[0]
    for mm in series_list[1:]:
        ll = ll.join(mm)
    ll['Gene_id'] = ll.index
    return ll

def read_gse140851(self, filename):
    series_list = []
    tar = tarfile.open(self.cache_location / filename)
    for member in tar.getmembers():
            f = tar.extractfile(member)
            sample = re.match('^[^.]+', member.name).group(0)
            readfile = gzip.open(f, 'rt', encoding="utf-8")
            df = pd.read_csv(readfile)
            df.set_index('Gene_id', inplace=True)
            df.rename(columns = {list(df)[-1]:sample}, inplace=True)
            series_list.append(df)
    tar.close()
    ll = series_list[0]
    for mm in series_list[1:]:
        ll = ll.join(mm)
    ll['Gene_id'] = ll.index
    return ll
