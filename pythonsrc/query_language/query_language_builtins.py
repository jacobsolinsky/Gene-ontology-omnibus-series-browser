from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests
import pandas as pd
from ..environment import environment
from ..mast.parse import calculate_p_values
from ..genes.ensembl import Gene
from ..organisms.taxonid import Species
GeneTable = Gene.GeneTable
import biomart
from io import StringIO
import requests, os, json, re
import itertools as it
import csv

#server =  biomart.BiomartServer( "http://useast.ensembl.org/biomart" )
#mmusculus =  server.datasets['mmusculus_gene_ensembl']
#mmusculus_sequences =  server.datasets['mmusculus_genomic_sequence']
species = Species(10090)

def multiple_t_tests(a, b, method=None):
    result = ttest_ind(a, b, axis=1).pvalue
    if method:
        result = multipletests(result, method=method)[1]
    return pd.Series(result, index=a.index)



class SampleSet:
    def __init__(self, d):
        self.d = d

    def __getattr__(self, k):
        return getattr(self, 'd')[k]


def construct_sample_set():
    return SampleSet({**environment.samples})

def add_to_gene_table(data_frame, type):
    ind = list(data_frame.index)
    ids = [str(x).split('///')[0] for x in ind]
    compids = [str(compid) for compid in GeneTable.table[type]]
    ids = [i for i in ids if str(i) not in compids]
    names = [
    'ensembl_gene_id', 'entrezgene_id', 'mgi_symbol',
    'transcription_start_site', 'chromosome_name', 'transcript_tsl', 'strand']
    i = 0
    retval = []
    print('to be added', len(ids))
    while True:
        chunk = ids[i:i + 100]
        i += 100
        if not chunk:
            break
        else:
            subtable= pd.read_table(StringIO(mmusculus.search({
                    'filters': {type: chunk},
                    'attributes':names,
                    }
                ).text), names=names)
            GeneTable.add(subtable)
        print(i)
    return GeneTable.table

def add_sequences(gene_table):
    input_genes = [Gene(**row._asdict()) for row in gene_table.itertuples()]
    genes = [
        g for g in input_genes if not os.path.exists(
            g.SEQUENCEDIR / f'{g.species}:{g.chromosome_name}:{g.transcription_start_site - g.upstream}..{g.transcription_start_site + g.downstream}:{g.strand}'
        )
    ]
    server = "https://rest.ensembl.org"
    ext = "/sequence/region/mus_musculus"
    headers={ "Content-Type" : "application/json", "Accept" : "application/json"}
    i = 0
    while True:
        print('adding_sequences', i)
        chunk = genes[i:i+49]
        if not chunk:
            break
        else:
            i += 49
            data = json.dumps({ "regions" : [
                f'{g.chromosome_name}:{g.transcription_start_site - g.upstream}..{g.transcription_start_site + g.downstream}:{g.strand}' for g in chunk
                ]
                })
            r = requests.post(server+ext, headers=headers, data=data
            )
            response = r.json()
            for r in response:
                id = re.match(r'[^:]+:[^:]+:(.+)', r['id']).group(1)
                id = re.sub(r'([^:]+:[^:]+):(.+)', r'\1..\2', id)
                with open(Gene.SEQUENCEDIR / f"mus_musculus:{id}", 'w+') as f:
                    f.write(r['seq'])
    return input_genes

def transcription_factor_analyze(genes, pfms=species.transcription_factor_matrices, name='output'):
    retval = calculate_p_values(pfms, genes)
    retval['tfs'] = retval['tfs'].apply(lambda x: species.transcription_factor_motifs[x]['name'])
    combodict = {}
    i = 1
    def tally_combos(df):
        nonlocal i
        print(i)
        i += 1
        combos = [it.combinations(df['tfs'], i) for i in range(1,4)]
        combos = [frozenset(combo) for combolist in combos for combo in combolist]
        for combo in combos:
            combodict[combo] = combodict.get(combo, 0) + 1
    retval.groupby('ids').apply(tally_combos)
    with open(f'results/{name}_combos.csv', 'w+') as f:
        for k, v in combodict.items():
            f.write(' | '.join(k))
            f.write(', ')
            f.write(str(v))
            f.write('\n')
    return retval

def get_best_tss(genes, groupby='mgi_symbol'):
    genes = genes.assign(tsl_level = lambda x: x['transcript_tsl'].map(lambda y: ord((str(y) + 'nnnn')[3])))
    genes = genes.loc[genes['tsl_level'] == ord('1')]
    return genes.sort_values('tsl_level').groupby(groupby, as_index=False).first().drop('tsl_level', axis=1)


def str_split(x):
    return x.map(lambda y: str(y).split('///')[0])
