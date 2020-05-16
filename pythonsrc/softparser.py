#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 11:07:33 2019

@author: Lab
"""
# pip install xlrd is necessary
from itertools import chain
from warnings import warn
import re
import pandas as pd
import numpy as np
from ftplib import FTP
from io import StringIO
import tempfile
import gzip
from functools import lru_cache
from io import BytesIO
import base64
from scipy.stats import ttest_ind
from scipy.stats import pearsonr

from statsmodels.stats.multitest import multipletests
import json
from pathlib import Path
import os
from .genes.ensembl import Gene
from .organisms.taxonid import Species
from .environment import environment
from .readexpressiontable import data_table_from_file


class GeoEntity:
    def __init__(self, family, accession_id, **kwargs):
        self.family, self.accession_id = family, accession_id
        self.cache_location = environment.CACHE_LOCATION / self.family.accession_id / self.accession_id
        os.makedirs(self.cache_location, exist_ok=True)
        self.metadata = {}
        self.flags = set()
        for key, value in kwargs.items():
            setattr(self, key, value)
            self.metadata[key] = value

    def __repr__(self):
        return f'{self.accession_id}'


class GeoDatabase(GeoEntity):
    pass


class GeoPlatform(GeoEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.Platform_technology not in (
          "in situ oligonucleotide", "spotted DNA/cDNA",
          "high-throughput sequencing", "oligonucleotide beads"):
            raise NotImplementedError(
                f"{self.Platform_technology} not supported"
            )

class GeoSeries(GeoEntity):
    pass


class GeoSample(GeoEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.has_data_table:
            if hasattr(self, 'Series_supplementary_file'):
                filename = self.Series_supplementary_file
                try:
                    self.data_table, self.filename = \
                        data_table_from_file(filename)
                    self.has_data_table = True
                    self.no_platform = True
                except:
                    pass


class GeoSampleWithDataTable(GeoSample):
    id_column = "ID_REF"
    value_column = "VALUE"

    @staticmethod
    def upgrade(geosample_instance):
        geosample_instance.__class__ = GeoSampleWithDataTable
        self = geosample_instance
        self.data_table[self.id_column] = self.data_table[
            self.id_column].astype(str)
        self.data_table.index = self.data_table[self.id_column].map(str)
        return self

    @property
    @lru_cache(maxsize=1)
    def gene_symbols(self):
        if hasattr(self, "no_platform"):
            return self.data_table[self.id_column]
        return self.subseries.gene_symbols

    @property
    @lru_cache(maxsize=1)
    def platform(self):
        return self.family.search(self.Sample_platform_id[0])

    @property
    @lru_cache(maxsize=1)
    def rank_normalized_expression(self):
        return self.data_table[self.value_column].rank()

    @property
    @lru_cache(maxsize=1)
    def percent_normalized_expression(self):
        return (
            100 * self.data_table[self.value_column].rank()
            / self.data_table[self.value_column].count()
        )

    @property
    def raw_expression(self):
        return self.data_table[self.value_column]

    @property
    @lru_cache(maxsize=1)
    def log2_expression(self):
        return np.log2(
            self.data_table[self.value_column]
            / sum(self.data_table[self.value_column])
        )

    def get_value(self, sequence_id, type_):
        series = {
            "raw": self.raw_expression,
            "percent": self.percent_normalized_expression,
            "rank": self.rank_normalized_expression,
            "log2": self.log2_expression,
            }[type_]
        retdict = {}
        retdict['VALUE'] = [series[sequence_id]]
        retval = pd.DataFrame(retdict)
        retval.index = [self.accession_id]
        return retval







class GeoSubseries(GeoEntity):
    def __init__(self):
        environment.species = self.species

    @property
    @lru_cache(maxsize=1)
    def group_columns(self):
        return [
            s for s, v in self.sample_columns.items()
            if v.get('group')
        ]

    @property
    @lru_cache(maxsize=1)
    def gene_symbols(self):
        return self.data_table[self.gene_column]

    @property
    @lru_cache(maxsize=1)
    def groups(self):
        retval = {}
        for k in self.sample_columns:
            retval.add(k)
        return list(retval)

    def gene_to_sequence_id(self, gene):
        return self.data_table[
                self.data_table[self.gene_column] == gene
                ][self.id_column].index[0]

    def sequence_id_to_gene(self, id):
        return self.data_table.loc[id][self.gene_column]

    def sequence_id_to_entrez_id(self, id):
        return self.data_table.loc[id][self.entrez_column]

    def sequence_id_to_gene_object(self, id):
        return Gene(entrez_id = self.sequence_id_to_entrez_id(id))

    from ._plots import plot_values, plot_dendrogram, plot_two_genes, plot_process
    from ._stats import (compare, column_cov, get_highest_comparisons, get_highest_correlations,
                         PVALUE_CORRECTION_METHODS, ttest)

    @lru_cache(maxsize=3)
    def sample_array_dict(self, type_):
        sample_group_dict = {}
        gv = self.get_all_values(type_=type_)
        for k, v in self.sample_columns.items():
            if v.get('group'):
                if not v['group'] in sample_group_dict:
                    sample_group_dict[v['group']] = []
                sample_group_dict[v['group']].append(k)
        return {
            k: gv.loc[:, v] for k, v in sample_group_dict.items()
        }

    @property
    def sample_columns(self):
        if not hasattr(self, '_sample_columns'):
            if os.path.exists(self.cache_location / 'sample_columns.json'):
                with open(self.cache_location / 'sample_columns.json') as f:
                    self._sample_columns = json.load(f)
            else:
                self._sample_columns = {}
        return self._sample_columns

    @sample_columns.setter
    def sample_columns(self, value):
        if value != self._sample_columns:
            self._sample_columns = value
            with open(self.cache_location / 'sample_columns.json', 'w+') as f:
                json.dump(value, f)



class GeoPlatformSubseries(GeoSubseries):
    data_source = "soft"
    id_column = "ID"
    entrez_column = "ENTREZ_GENE_ID"
    gene_regex = r"gene[ _]?(symbol)"

    def __init__(self, platform, samples, family_accession_id):
        self.family_accession_id = family_accession_id
        self.platform = platform
        self.cache_location = environment.CACHE_LOCATION / self.family_accession_id / f'{self.platform.accession_id}_x_{self.family_accession_id}'
        os.makedirs(self.cache_location, exist_ok = True)
        self.samples = samples
        for s in self.samples:
            s.subseries = self
            s = GeoSampleWithDataTable.upgrade(s)
        self.platform.data_table[self.id_column] = \
            self.platform.data_table[self.id_column].astype(str)
        self.platform.data_table.index = \
            self.platform.data_table[self.id_column].map(str)
        for c in self.platform.data_table.columns:
            if re.match(self.gene_regex, c, re.IGNORECASE):
                self.gene_column = c
                break
            else:
                self.gene_column = self.id_column
        environment.platform = self.platform
        super().__init__()


    @property
    @lru_cache(maxsize=1)
    def columns(self):
        return {
            s.accession_id: {
                'value': list(s.data_table[s.value_column].iloc[0:10])
            }
            for s in self.samples
        }
    @property
    def species(self):
        if not hasattr(self, '_species'):
            self._species = Species(taxonid=self.platform.metadata['Platform_taxid'][0])
        return self._species


    @property
    @lru_cache(maxsize=1)
    def data_table(self):
        return self.platform.data_table


    def get_values(self, sequence_id, type_):
        retlist = [
            s.get_value(sequence_id, type_) for s in self.samples
            if s.accession_id in self.group_columns
        ]
        return pd.concat(retlist)

    def get_all_values(self, type_):
        series_type = {
            "raw": "raw_expression",
            "percent": "percent_normalized_expression",
            "rank": "rank_normalized_expression",
            "log2": "log2_expression",
            }[type_]
        return pd.DataFrame({
                s.accession_id: getattr(s, series_type)
                for s in self.samples if
                s.accession_id in self.group_columns
                })

    def __repr__(self):
        return f'Platform: {self.platform}, Samples: {self.samples}'


class GeoDataTableSubseries(GeoSubseries):
    data_source = "xlsx"

    def __init__(self, filename):
        self.filename = filename
        final_file_name = filename.split('/')[-1]
        self.cache_location = environment.CACHE_LOCATION / (final_file_name + '.info_cache')
        os.makedirs(self.cache_location, exist_ok=True)
        environment.platform = self.data_source
    data_table_from_file = data_table_from_file

    def __hash__(self):
        return hash(json.dumps(self.sample_columns, sort_keys=True))

    def __eq__(self, value):
        return self.sample_columns == value.sample_columns

    @property
    def data_table(self):
        if not hasattr(self, '_data_table'):
            self._data_table = self.data_table_from_file(self.filename)
        return self._data_table

    @property
    @lru_cache(maxsize=1)
    def columns(self):
        thing = {s: {
            'value': list(self.data_table[s].iloc[0:10])}
            for s in self.data_table.columns
        }
        return thing
    OBSERVED_ID_COLUMN_NAMES = (
        "gene id", "gene_id", "test id", "test_id",
        "gids", "id", "id_ref", 'ensembl_gene_id', 'gene_ensembl', 'alt name')

    @property
    @lru_cache(maxsize=1)
    def id_column(self):
        for c, v in self.sample_columns.items():
            if v.get('id'):
                self.data_table.index = self.data_table[c].map(str)
                return c
        self.identify_gene_and_id_column()
        for c, v in self.sample_columns.items():
            if v.get('id'):
                self.data_table.index = self.data_table[c].map(str)
                return c

    @property
    @lru_cache(maxsize=1)
    def gene_column(self):
        for c, v in self.sample_columns.items():
            if v.get('gene'):
                return c
        self.identify_gene_and_id_column()
        for c, v in self.sample_columns.items():
            if v.get('gene'):
                return c

    def identify_gene_and_id_column(self):
        generegex = r"gene[ _]?(assignment|symbol)?"
        idregex = fr"({'|'.join(self.OBSERVED_ID_COLUMN_NAMES)})"
        id_found, gene_found = False, False
        for column in self.data_table.columns:
            self.sample_columns[column] = {}
            if re.match(generegex, column, re.IGNORECASE):
                self.sample_columns[column]['gene'] = True
                gene_found = column
            if re.match(idregex, column, re.IGNORECASE):
                self.sample_columns[column]['id'] = True
                id_found = column
            if (not gene_found) and id_found:
                self.sample_columns[id_found]['gene'] = True

    def get_values(self, sequence_id, type_):
        series_data_frame = getattr(self, {
            "raw": "raw_expression",
            "percent": "percent_normalized_expression",
            "rank": "rank_normalized_expression",
            "log2": "log2_expression",
        }[type_])
        return pd.DataFrame({'VALUE': series_data_frame.loc[sequence_id]})

    def get_all_values(self, type_):
        return getattr(self, {
            "raw": "raw_expression",
            "percent": "percent_normalized_expression",
            "rank": "rank_normalized_expression",
            "log2": "log2_expression",
        }[type_])

    @property
    @lru_cache(maxsize=1)
    def rank_normalized_expression(self):
        return pd.DataFrame({
            s: self.data_table[s].rank()
            for s in self.group_columns
        })

    @property
    @lru_cache(maxsize=1)
    def percent_normalized_expression(self):
        return pd.DataFrame({
            s: 100 * self.data_table[s].rank() / self.data_table[s].count()
            for s in self.group_columns
        })

    @property
    def raw_expression(self):
        return pd.DataFrame({
            s: self.data_table[s]
            for s in self.group_columns
        })

    @property
    @lru_cache(maxsize=1)
    def log2_expression(self):
        return pd.DataFrame({
            s: np.log2((self.data_table[s] / sum(self.data_table[s])))
            for s in self.group_columns
        })

    @property
    def sample_columns(self):
        if not hasattr(self, '_sample_columns'):
            if os.path.exists(self.cache_location / 'sample_columns.json'):
                with open(self.cache_location / 'sample_columns.json') as f:
                    self._sample_columns = json.load(f)
            else:
                self._sample_columns = {}
        return self._sample_columns

    @sample_columns.setter
    def sample_columns(self, value):
        if value != self._sample_columns:
            self._sample_columns = value
            with open(self.cache_location / 'sample_columns.json', 'w+') as f:
                json.dump(value, f)
        self.data_table.index = self.data_table[self.id_column].map(str)


    def __repr__(self):
        return f'Subseries associated with {self.filename}'


class GeoFamily:
    def __init__(self, entity_dict, accession_id):
        self.accession_id = accession_id
        self.series = []
        self.platforms = []
        self.samples = []
        self.databases = []
        type_dict = {
                'SAMPLE': (GeoSample, self.samples),
                'SERIES': (GeoSeries, self.series),
                'PLATFORM': (GeoPlatform, self.platforms),
                'DATABASE': (GeoDatabase, self.databases),
         }
        for k, v in entity_dict.items():
            type_dict[k[0]][1].append(
                    type_dict[k[0]][0](self, k[1], **v.dict)
                    )

    def search(self, accession_id):
        for entity in chain(self.series, self.platforms, self.samples, self.databases):
            if entity.accession_id == accession_id:
                return entity
    ACCEPTED_SUFFIXES = "xlsx", "tsv", "csv", "txt"
    SUFFIX_REGEX = fr"\.({'|'.join(ACCEPTED_SUFFIXES)})(\.gz)?$"

    @property
    @lru_cache(maxsize=1)
    def subseries_dict(self):
        subseries_dict = {}

        #First identifies samples that have their data attached to them. Assumes samples
        #With the same platform ID are comparable
        for sample in self.samples:
            if sample.has_data_table:
                if sample.Sample_platform_id[0] not in subseries_dict:
                    subseries_dict[sample.Sample_platform_id[0]] = []
                subseries_dict[sample.Sample_platform_id[0]].append(sample)
        for k, v in subseries_dict.items():
            subseries_dict[k] = GeoPlatformSubseries(self.search(k), v, self.accession_id)

        #Then extracts data stored at the series level
        this_series = self.series[0]
        if hasattr(this_series, 'Series_supplementary_file'):
            for filename in this_series.Series_supplementary_file:
                #if re.search(self.SUFFIX_REGEX, filename):
                subseries_dict[filename] = GeoDataTableSubseries(filename)

        #Raises an error if no data could be found
        if subseries_dict:
            return subseries_dict
        raise NotImplementedError("Only native soft files and xlsx files are supported")

    def __repr__(self):
        return (
f'''Series: {self.series}
Platforms: {self.platforms}
Samples: {self.samples}
Databases: {self.databases}''')




class AttributeSet:
    def __init__(self, obligations, flags, empty_lists, full_lists):
        self.obligations, self.flags, self.empty_lists, self.full_lists = \
        obligations, flags, empty_lists, full_lists
        self.dict = {}
        self.dict['data_table_header'] = {}
        self.dict['rows'] = []
        self.dict['data_table'] = None
        self.dict['has_data_table'] = False
        for i in chain(obligations, flags):
            self.dict[i] = None
        for i in chain(empty_lists, full_lists):
            self.dict[i] = []

    def __setitem__(self, key, value):
        if key not in self.dict:
            self.dict[key] = []
        if type(self.dict[key]) == list:
            self.dict[key].append(value)
        elif self.dict[key] is None:
            self.dict[key] = value
        elif key in chain(self.obligations, self.flags):
            warn(f"Multiple values for {key}, there should be only one")

    def __getitem__(self, key):
        return self.dict[key]

    def check(self):
        for i in self.obligations:
            if self.dict[i] is None:
                warn(f"No value for {i} found")
        for i in self.full_lists:
            if self.dict[i] == []:
                warn(f"no values for {i} found")

    def __repr__(self):
        return self.dict.__repr__()


platform_attribute_set = {
       "obligations": ["Platform_title",
                       "Platform_distribution",
                       "Platform_technology",
                       "Platform_manufacturer",
                       "platform_table_begin",
                       "platform_table_end"],
       "flags": ["Platform_support",
                 "Platform_coating",
                 "Platform_geo_accession",
                 "has_data_table"],
       "empty_lists": ["Platform_catalog_number",
                       "Platform_web_link",
                       "Platform_description",
                       "Platform_contributor",
                       "Platform_pubmed_id", ],
       "full_lists": ["Platform_organism",
                     "Platform_manufacture_protocol", ],
       }
null_attribute_set = {
    "obligations": [], "flags": ["has_data_table"],
    "empty_lists": [], "full_lists": []
}


class SoftFile:
    """This class downloads and parses the soft file indicated by its accession argument.
    The output is a dictionary keyed by tuples of the form (EntityIndicator, accession_id).
    If the input accession is a GSE family, the .family attribute will contain a
    GeoFamily instance, which associated  plotting and analysis functions
    with the downloaded data."""
    label_value_regex = r"([^=]+) = ([^\n]*)?"
    label_novalue_regex = r"[^\n]+"

    def entity_indicator_line(self, line):
        groups = re.match(self.label_value_regex, line)
        if groups[1] == "PLATFORM":
            self.entity_dict[(groups[1], groups[2])] = AttributeSet(**platform_attribute_set)
        else:
            self.entity_dict[(groups[1], groups[2])] = AttributeSet(**null_attribute_set)
        self.current_entity = (groups[1], groups[2])

    def entity_attribute_line(self, line):
        groups = re.match(self.label_value_regex, line)
        if not groups:
            groups = re.match(self.label_novalue_regex, line)
            self.entity_dict[self.current_entity][groups[0]] = ""
            if groups[0] == "platform_table_begin":
                self.entity_dict[self.current_entity]["has_data_table"] = True
            else:
                self.construct_data_frame()
        else:
            self.entity_dict[self.current_entity][groups[1]] = groups[2]

    def data_table_header_description_line(self, line):
        groups = re.match(self.label_value_regex, line)
        self.entity_dict[self.current_entity]["data_table_header"][groups[1]] = groups[2]

    def other_line(self, line):
        self.entity_dict[self.current_entity]["rows"].append(line)

    def __init__(self, accession, full=False):
        self.header, self.has_data_table = False, False
        accession = accession.upper()
        self.accession = accession
        self.entity_dict = {}
        if not os.path.exists(environment.CACHE_LOCATION / accession):
            os.makedirs(environment.CACHE_LOCATION / accession)
            shortpath = re.sub("\d{1,3}$", "nnn", accession)
            path = {
                    "GDS": f"geo/datasets/{shortpath}/{accession}/soft/{accession}{'_full' if full else ''}.soft.gz",
                    "GPL": f"geo/platforms/{shortpath}/{accession}/soft/{accession}_family.soft.gz",
                    "GSE": f"geo/series/{shortpath}/{accession}/soft/{accession}_family.soft.gz",
                    }[accession[:3]]
            ftp = FTP('ftp.ncbi.nlm.nih.gov')
            ftp.login()
            with open(environment.CACHE_LOCATION / accession / "soft.gz", "wb+") as f:
                ftp.retrbinary(f'RETR {path}', f.write)
            ftp.close()
        with open(environment.CACHE_LOCATION / accession / "soft.gz", "rb") as f:
            with gzip.open(f, 'rt', encoding="utf-8") as g:
                for line in g:
                    self.lineclassify(line)
        for v in self.entity_dict.values():
            v.check()


    @property
    def family(self):
        return GeoFamily(self.entity_dict, self.accession)



    def lineclassify(self, line):
        line_mappings = {
            "^": self.entity_indicator_line,
            "!": self.entity_attribute_line,
            "#": self.data_table_header_description_line,
            }
        if line[0] == "^":
            print(line)
        if line[0] not in line_mappings.keys():
            lineref = line
        else:
            lineref = line[1:]
        line_mappings.get(line[0], self.other_line)(lineref)

    def construct_data_frame(self):
        try:
            a = self.entity_dict[self.current_entity]["rows"]
            if a:
                self.entity_dict[self.current_entity]["data_table"] = pd.read_table(
                        StringIO(''.join(a)))
                self.entity_dict[self.current_entity]["has_data_table"]= True
        except pd.io.common.EmptyDataError:
            self.entity_dict[self.current_entity]["data_table"] = None
            self.has_data_table= False
