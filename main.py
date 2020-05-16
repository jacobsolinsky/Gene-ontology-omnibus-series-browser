


from flask import Flask, render_template, request
from pythonsrc.softparser import SoftFile
from pythonsrc.environment import environment
import simplejson
import ftplib
import os
import pandas as pd
import numpy as np
from pythonsrc.query_language.parser import parse

def my_converter(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, datetime.datetime):
            return obj.__str__()

thing = None
fileDir = os.path.dirname(os.path.abspath(__file__))


app = Flask(__name__)



@app.route('/')
def index():
    return render_template("index.html")

@app.route('/app.js')
def serve_raw():
    with open(os.path.join(fileDir, 'dist/js/app.js')) as f:
        return f.read()

@app.route('/app.js.map')
def serve_map():
    with open(os.path.join(fileDir, 'dist/js/app.js.map')) as f:
        return f.read()



@app.route('/download-gse')
def download_gse():
    gse = request.args.get('gse')
    print(gse)
    try:
        environment.family = SoftFile(gse).family
        return simplejson.dumps({
            'subseries': list(environment.family.subseries_dict),
            }, ignore_nan=True)
    except NotImplementedError as e:
        return simplejson.dumps({
            'subseries': [],
            'exception': str(e),
            }, ignore_nan=True)
    except ftplib.error_perm:
        return simplejson.dumps({
            'subseries': [],
            'exception': f'Series family softfile for accession {gse} does not exist',
            }, ignore_nan=True)


@app.route('/select-subseries', methods=["POST"])
def select_subseries():
    subseriesId = request.get_json(force=True).get('subseriesId')
    environment.subseries = environment.family.subseries_dict[subseriesId]
    print('herer')
    return simplejson.dumps({
        'data_source': environment.subseries.data_source,
        'excelColumns': environment.subseries.columns,
        'sample_columns': environment.subseries.sample_columns,
        }, ignore_nan=True, default=my_converter)


@app.route('/set-sample-columns', methods=["POST"])
def set_subseries():
    sample_columns = request.get_json(force=True).get('sample_columns')
    environment.subseries.sample_columns = sample_columns
    gs = pd.DataFrame({'gene': environment.subseries.gene_symbols},
                      index=environment.subseries.data_table.index)
    gs['id'] = gs.index
    gs['customlabel'] = gs["gene"].map(str) + " ` " + gs["id"].map(str)
    return simplejson.dumps({
        'genes': list(gs['customlabel']),
    }, ignore_nan=True)



@app.route('/gene-plot', methods=["POST"])
def gene_plot():
    gene = request.get_json(force=True).get('gene')
    type_ = request.get_json(force=True).get('type_')
    genePlotImage, genePlotTable = environment.subseries.plot_values(gene, type_)
    geneCorrelationTable = environment.subseries.get_highest_correlations(gene).to_json(orient="records")
    return simplejson.dumps({
        "genePlotImage": genePlotImage,
        "genePlotTable": genePlotTable,
        "geneCorrelationTable": geneCorrelationTable,
        })


@app.route('/plot-two-genes', methods=["POST"])
def plot_two_genes():
    gene1 = request.get_json(force=True).get('gene1')
    gene2 = request.get_json(force=True).get('gene2')
    twoGenePlotImage, twoGenePlotTable = environment.subseries.plot_two_genes(gene1, gene2)
    return simplejson.dumps({
        "twoGenePlotImage": twoGenePlotImage,
        "twoGenePlotTable": twoGenePlotTable,
        })

@app.route('/plot-dendrogram', methods=["POST"])
def plot_dendrogram():
    type_ = request.get_json(force=True).get('type_')
    dendrogramImage = environment.subseries.plot_dendrogram(type_)
    return simplejson.dumps({
        "dendrogramImage": dendrogramImage,
        })

@app.route('/gene-expression-compare', methods=["POST"])
def gene_expression_compare():
    method = request.get_json(force=True).get('method')
    print(method)
    gene_expression_compare_table = environment.subseries.get_highest_comparisons(method=method).to_html()
    return simplejson.dumps({
            "gene_expression_compare_table": gene_expression_compare_table,
            })


@app.route('/get-pvalue-correction-methods')
def get_pvalue_correction_methods():
    pvalue_correction_methods = environment.subseries.PVALUE_CORRECTION_METHODS
    return simplejson.dumps({
            "pvalue_correction_methods": pvalue_correction_methods,
            })

@app.route('/commandline', methods=["POST"])
def commandline():
    command = request.data.decode('utf8')
    return str(parse(command))

# With debug=True, Flask server will auto-reload
# when there are code changes
if __name__ == '__main__':
	app.run(port=5000, debug=True)
