import requests, os
import xml.etree.ElementTree as ET
from Bio.motifs import Motif
import json
EUTILS_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
from Bio import motifs
from ..environment import environment


class SpeciesNotFoundError(Exception):
    pass

class Species:
    CACHE_LOCATION = environment.CACHE_LOCATION / 'species'
    os.makedirs(CACHE_LOCATION, exist_ok=True)
    def __init__(self, taxonid = None, scientific_name = None):
        assert taxonid or scientific_name, "Species must have taxon id or scientific name"
        self._taxonid = taxonid
        self._scientific_name = scientific_name

    @property
    def transcription_factor_matrices(self):
        if not os.path.exists(self.cache_location / 'transcription_factor_matrices.json'):
            tms = taxonid_to_jaspar_matrix_ids(self.taxonid)
            write_tms = {k: v.counts for k, v in tms.items()}
            with open(self.cache_location / 'transcription_factor_matrices.json', 'w+') as f:
                json.dump(write_tms, f)
            self._transcription_factor_matrices = tms
        elif not hasattr(self, '_transcription_factor_matrices'):
            with open(self.cache_location / 'transcription_factor_matrices.json') as f:
                write_tms = json.load(f)
            tms = {k: Motif(counts = v) for k, v in write_tms.items()}
            self._transcription_factor_matrices = tms
        return self._transcription_factor_matrices

    @property
    def transcription_factor_motifs(self):
        if not hasattr(self, '_transcription_factor_motifs'):
            with open(self.cache_location / 'matrix_info.json') as f:
                retdict = {}
                for e in json.load(f):
                    retdict[e['matrix_id']] = e
                self._transcription_factor_motifs =  retdict
        return self._transcription_factor_motifs

    @property
    def scientific_name(self):
        if self._scientific_name is None:
            self._scientific_name = taxonid_to_scientific_name(self.taxonid)
        return self._scientific_name

    @property
    def taxonid(self):
        if self._taxonid is None:
            self._taxonid = scientific_name_to_taxonid(self.scientific_name)
        return self._taxonid

    def __repr__(self):
        return f"{self.scientific_name}: taxonid {self.taxonid}"

    @property
    def cache_location(self):
        sn = '_'.join(self.scientific_name.split(' '))
        if not os.path.exists(self.CACHE_LOCATION / f"{sn}: taxonid {self.taxonid}"):
            os.makedirs(self.CACHE_LOCATION / f"{sn}: taxonid {self.taxonid}")
        return self.CACHE_LOCATION / f"{sn}: taxonid {self.taxonid}"


def scientific_name_to_taxonid(name):
    input_name = name.translate(str.maketrans(' ', '+'))
    r = ET.fromstring(requests.get(EUTILS_URL + f'esearch.fcgi?db=taxonomy&term={input_name}').content)
    try:
        retval = r.find('IdList').find('Id').text
        return retval
    except AttributeError:
        raise SpeciesNotFoundError(name)


def taxonid_to_scientific_name(id):
    r = ET.fromstring(requests.get(EUTILS_URL + f'efetch.fcgi?db=taxonomy&id={id}').content)
    try:
        retval = r.find('Taxon').find('ScientificName').text
        return retval
    except AttributeError:
        return SpeciesNotFoundError(f'Taxonid: {id}')


def taxonid_to_jaspar_matrix_ids(taxonid):
    retval = {}
    r = requests.get(f'http://jaspar.genereg.net/api/v1/species/{taxonid}').json()
    page = 1
    while True:
        print(f'Retrieveing transcription factors for {taxonid} page {page}')
        page += 1
        for result in r['results']:
            retval[result['matrix_id']] = jaspar_matrix_id_to_motif(result['matrix_id'])
        if r['next']:
            r = requests.get(r['next']).json()
        else:
            break
    return retval

def jaspar_matrix_id_to_motif(matrix_id):
    return Motif(
        counts=requests.get(f'http://jaspar.genereg.net/api/v1/matrix/{matrix_id}/').json()['pfm'])
