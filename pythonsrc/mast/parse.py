from xml.etree import ElementTree as ET
import os
import pandas as pd
def extract_pvalue():
    a = ET.parse('mast_out/mast.xml')
    ids = []
    pvalues = []
    tfs = []
    seqs = a.findall('./sequences/sequence')
    motifs = [el.attrib['id'] for el in a.findall('./motifs/motif')]
    for seq in seqs:
        for hit in seq.findall('seg/hit'):
            ids.append(seq.attrib['name'])
            tfs.append(motifs[int(hit.attrib['idx'])])
            pvalues.append(hit.attrib['pvalue'])
    return pd.DataFrame({'ids': ids, 'pvalues': pvalues, 'tfs': tfs})

def mast_table(pfm):
    name = pfm.name
    pwm = pfm.pwm
    ays, cys, tys, gys = pwm['A'], pwm['C'], pwm['T'], pwm['G']
    inner = ''.join(
        [f'{a} {c} {g} {t}\n' for a, c, g, t in zip(ays, cys, tys, gys)]
    )
    return f'''
MOTIF {name}
letter-probability matrix:
{inner}
'''


def write_mast(pfms):
    for k, v in pfms.items():
        v.name = k
    inner = ''.join([mast_table(pfm) for pfm in pfms.values()])
    with open('motif.meme', 'w+') as f:

        f.write(
        f'''MEME version 4

ALPHABET= ACGT

strands: + -

{inner}
 '''
         )

def write_fasta(genes):
    with open('seq.fasta', 'w+') as f:
        for g in genes:
            f.write(f'>{g.mgi_symbol}\n')
            f.write(f'{g.promoter_sequence}\n')

def calculate_p_values(pfms, genes):
    write_mast(pfms)
    write_fasta(genes)
    os.system('mast motif.meme seq.fasta -notext -nohtml -w')
    retval = extract_pvalue()
    #os.system('rm -rf mast_out')
    #os.system('rm motif.meme')
    #os.system('rm seq.fasta')
    return retval
