import numpy as np
import pandas as pd

def compare(self, type_='raw', method='fdr_bh'):
    data_frame_dict = self.sample_array_dict(type_)
    if len(data_frame_dict) == 2:
        pvalues = ttest_ind(*data_frame_dict.values(), axis=1).pvalue
        if method:
            return multipletests(pvalues, method)[1]
        return pvalues


def get_highest_comparisons(self, type_='raw', method='fdr_bh'):
    all_values = self.get_all_values('raw')
    covmat = self.compare(type_, method)
    inspect_frame = \
        pd.DataFrame(covmat, index=all_values.index, columns=['pvalue'])
    inspect_frame = \
        inspect_frame.sort_values(by='pvalue', ascending=False).iloc[0:20]
    inspect_frame['id'] = inspect_frame.index
    inspect_frame['gene'] = [
        f'{self.sequence_id_to_gene(id)} ` {id}'
        for id in inspect_frame.index
    ]
    return inspect_frame


@staticmethod
def column_cov(x, i):
    print(x)
    y = x[i]
    ex = np.mean(x, axis=1)
    ey = np.mean(y)
    sx = x - ex.reshape(len(ex), 1)
    sy = y - ey
    sxy = sx * sy
    sumxy = np.sum(sxy, axis=1)
    n = x.shape[1]
    cov = sumxy / n
    sdx = np.std(x, axis=1)
    sdy = np.std(y)
    sd = sdx * sdy
    return cov / sd


def ttest(self, bonferroni):
    pass


def get_highest_correlations(self, input_id):
    all_values = self.get_all_values('raw')
    input_i = all_values.index.get_loc(input_id)
    covmat = np.absolute(self.column_cov(np.array(all_values), input_i))
    inspect_frame = pd.DataFrame(
        covmat, index=all_values.index, columns=["Correlation"]
    )
    inspect_frame = \
        inspect_frame.sort_values(
            by="Correlation", ascending=False
        ).iloc[0:20]
    inspect_frame['id'] = inspect_frame.index
    inspect_frame['gene'] = [
        f'{self.sequence_id_to_gene(id)} ` {id}'
        for id in inspect_frame.index
    ]
    return inspect_frame
PVALUE_CORRECTION_METHODS = (
    'bonferroni', 'sidak', 'holm-sidak', 'holm', 'simes-hochberg',
    'hommel', 'fdr-bh', 'fdr-by', 'fdr_tsbh', 'fdr_tsbky',
)
