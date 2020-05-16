
import requests
import os
from ..environment import environment
import pandas as pd


class Gene:
    species = 'mus_musculus'
    upstream = 1000
    downstream = 0
    SEQUENCEDIR = environment.CACHE_LOCATION / 'sequences'
    os.makedirs(SEQUENCEDIR, exist_ok=True)
    class GeneTable:
        SEQUENCEDIR = environment.CACHE_LOCATION / 'sequences'
        GENE_ID_TABLE_LOC = SEQUENCEDIR / "genetable.csv"
        if not os.path.exists(GENE_ID_TABLE_LOC):
            with open(GENE_ID_TABLE_LOC, 'w+') as f:
                table = pd.DataFrame(columns = ['ensembl_gene_id', 'entrezgene_id', 'mgi_symbol', 'start_site'])
                table.to_csv(f, index=False)
        else:
            with open(GENE_ID_TABLE_LOC, 'r') as f:
                table = pd.read_csv(f)

        @classmethod
        def add(cls, df):
            cls.table = pd.concat([cls.table, df]).drop_duplicates()
            with open(cls.GENE_ID_TABLE_LOC, 'w+') as f:
                cls.table.to_csv(f, index=False)
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if k in [
            'ensembl_gene_id', 'entrezgene_id', 'mgi_symbol',
            'transcription_start_site', 'chromosome_name', 'transcript_tsl', 'strand'
            ]:
                setattr(self, k, v)
        self.strand = int(self.strand)
        self.transcription_start_site = int(self.transcription_start_site)
    @property
    def code(self):
        return f'{self.species}:{self.chromosome_name}:{self.transcription_start_site - self.upstream}..{self.transcription_start_site + self.downstream}:{self.strand}'
    @property
    def promoter_sequence(self, upstream=1000, downstream=0):
        if not hasattr(self, '_promoter_sequence'):
            try:
                with open(self.SEQUENCEDIR / self.code) as f:
                    self._promoter_sequence = f.read()
            except FileNotFoundError:
                raise FileNotFoundError('Please call add_sequences')
        return self._promoter_sequence
