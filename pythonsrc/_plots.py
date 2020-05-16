from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
from io import BytesIO
import base64


def plot_values(self, sequence_id, type_, from_symbol=True):
    gene = f'{self.sequence_id_to_gene(sequence_id)} ` {sequence_id}'
    plot_data = self.get_values(sequence_id, type_)
    plot_data = plot_data.dropna()
    groups = [sample.get('group') for sample in self.sample_columns.values() if sample.get('group')]
    print(plot_data)
    print(groups)
    save_plot = sns.relplot(
        data=plot_data, x=list(range(len(plot_data.index))),
        y='VALUE', hue=groups
    )
    save_plot.set(
        xlabel=f"sample", ylabel=f'{gene} {type_} expression'
    )
    title_string = f'<tr><th>Group</th><th>{type_} expression</th></tr>'
    value_string = ''.join(
        f"<tr><td>{m}</td><td>{n}</td></tr>"
        for m, n in zip(groups, plot_data['VALUE'])
    )
    return (self.plot_process(save_plot),
            f'<table>{title_string}{value_string}</table>')


def plot_dendrogram(self, type_):
    df = np.transpose(self.get_all_values(type_))
    z = linkage(df, method="ward", metric="euclidean")
    save_plot = plt.figure()
    dendrogram(z, labels=list(df.index), leaf_rotation=90)
    return self.plot_process(save_plot)


def plot_two_genes(self, sequence_id1, sequence_id2, type_="raw"):
    gene1 = f'{self.sequence_id_to_gene(sequence_id1)} ` {sequence_id1}'
    gene2 = f'{self.sequence_id_to_gene(sequence_id2)} ` {sequence_id2}'
    plot_data1 = self.get_values(sequence_id1, type_).dropna()['VALUE']
    plot_data2 = self.get_values(sequence_id2, type_).dropna()['VALUE']
    plot_data = pd.DataFrame({'x': plot_data1, 'y': plot_data2})
    groups = [sample['group'] for sample in self.sample_columns.values() if sample.get('group')]
    save_plot = sns.relplot(data=plot_data, x='x', y='y', hue=groups)
    save_plot.set(
        xlabel=f"{gene1} expression", ylabel=f'{gene2} expression'
    )
    plt.show()
    title_string = \
        f'<tr><th>{gene1} expression</th><th>{gene2} expression</th></tr>'
    value_string = ''.join(
        f"<tr><td>{m}</td><td>{n}</td></tr>"
        for m, n in zip(plot_data1, plot_data2)
    )
    return (self.plot_process(save_plot),
            f'<table>{title_string}{value_string}</table>')


@staticmethod
def plot_process(save_plot):
    figfile = BytesIO()
    save_plot.savefig(figfile, format='png')
    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue()).decode('utf-8')
    return f'<img src="data:image/png;base64,{figdata_png}">'
