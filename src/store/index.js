import Vue from 'vue'
import Vuex from 'vuex'
import comparison from './comparison.js'

Vue.use(Vuex)


export default new Vuex.Store({
  state: {
        //General params
        _error: false,
        error: "",
        gse: "",
        _gseDownloaded: false,
        _gseDownloading: false,
        _subseriesSelected: false,
        _geoDataTableSubseries: false,
        subseries: [],
        subseriesId: "",
        //Dendrogram params
        _dendrogram: false,
        dendrogramImage: "",
        //Individual Gene Plot params
        _genePlot: false,
        genePlotImage: "",
        genePlotTable: "",
        geneCorrelationTable: "",
        excelColumns: [],
        genes: [],
        gene: "",
        type_s: ['rank', 'percent', 'raw'],
        type_: "percent",
        _plotTwoGenes: false,
        twoGenePlotImage: "",
        twoGenePlotTable: "",
  },
  //commit mutations
  mutations: {
    setGene(state, param){state.gene = param},
    setType_(state, param){state.type_ = param},
    setSubseriesId(state, param){state.subseriesId = param},
    setExcelColumns(state, param){state.excelColumns = param},
  },
  //distpatct actions
  actions: {
    download_gse({dispatch, commit, state}, gse_accession_id){
      state._error = false
      dispatch('gseDownloading')
      fetch(`/download-gse?gse=${gse_accession_id}`).
        then(response => response.json()).
        then(data => {if (data.subseries.length > 0){
                      state.subseries = data.subseries
                      dispatch('gseDownloaded')
                    }
                    else {
                      dispatch('error', data.exception)
                    }

            })
      },
      error({dispatch, state}, error){
        state.error = error
        state._error = true
        state._gseDownloading = false
        state._gseDownloaded = false
        dispatch('invalidateSubseriesSelected')
      },
      gseDownloading({dispatch, state}){
        state.subseries = []
        state._gseDownloading = true
        state._gseDownloaded = false
        dispatch('invalidateSubseriesSelected')
      },

      gseDownloaded({dispatch, state}){
        state._gseDownloading = false
        state._gseDownloaded = true
      },

      invalidateSubseriesSelected({dispatch, state}){
        state._subseriesSelected = false
        state.subseriesId = ""

        state._dendrogram = false
        dispatch('invalidateColumnsAvailable')
      },

      invalidateColumnsAvailable({dispatch, state}){
        state._selectSampleColumns = false
        state.excelColumns = []
        state.gene_id_needed = false
        dispatch('invalidateGenePlotParamsAvailable')
      },

      invalidateGenePlotParamsAvailable({dispatch, state}){
        state._genePlotParamsAvailable = false
        state._genePlot = false
        state.genePlotImage = ""
        state.geneCorrelationTable = ""
        state.gene = ""
        state.type_ = "percent"
        state._plotTwoGenes = false
      },

      select_subseries({state, dispatch}, subseriesId){
        dispatch('invalidateColumnsAvailable')
        fetch(`/select-subseries`, {body: JSON.stringify({
                                            subseriesId: subseriesId
                                         }),
                                   method: "POST"}).
          then(response => response.json()).
          then(data => {
              var o = {}
              var ec = {... data.excelColumns, ... data.sample_columns}
              Object.keys(data.excelColumns).forEach((item, index) =>{
                o[item] = {
                  group: ec[item].group ?ec[item].group:"",
                  id: ec[item].id,
                  gene: ec[item].gene,
                  values: ec[item].value,
                  get checked() {return this.group.length > 0| this.id | this.gene}
                }
              })
              state.excelColumns = o
              state._subseriesSelected = true
              state.gene_id_needed = !(data.data_source === "soft")
              dispatch('set_sample_columns')
            })
        },

        set_sample_columns({state, dispatch}){
          console.log('asdads')
          function filterObject(o){
            var id = false
            var gene = false
            var n = {}
            Object.keys(o).forEach(i => {
              if (o[i].checked){
                n[i] = o[i]
              }
              if (o[i].gene) { gene = true}
              if (o[i].id) { id = true}
            })
            if ((gene & id) | (!state.gene_id_needed)){
                        return n
            }
            return {}
          }
          let sample_columns = filterObject(state.excelColumns)
          if (Object.keys(sample_columns).length > 0){
            dispatch('invalidateGenePlotParamsAvailable')
            fetch(`/set-sample-columns`, {body: JSON.stringify({
                                            sample_columns: sample_columns,
                                             }),
                                       method: "POST"}).
              then(response => response.json()).
              then(data => {
                  state.genes = data.genes
                })
            }
          },

      updateGenePlotParams({commit, state, getters}, key, value){
        function filterObject(o){
          var id = false
          var gene = false
          var n = {}
          Object.keys(o).forEach(i => {
            if (o[i].checked){
              n[i] = o[i]
            }
            if (o[i].gene) { gene = true}
            if (o[i].id) { id = true}
          })
          if ((gene & id) | (!state.gene_id_needed)){
                      return n
          }
          return {}
        }
        let sample_columns = filterObject(state.excelColumns)
        var conditions = state.gene.length > 0 & state.type_.length > 0 & Object.keys(sample_columns).length > 0
        if (conditions) {
          fetch(`/gene-plot`, {body: JSON.stringify({gene: /.* ` (.*)$/.exec(state.gene)[1],
                                                     type_: state.type_,
                                           }),
                                     method: "POST"}).
            then(response => response.json()).
            then(data => {
              state.genePlotImage = data.genePlotImage
              state.genePlotTable = data.genePlotTable
              state.geneCorrelationTable = JSON.parse(data.geneCorrelationTable)
              state._genePlot = true
            })
        }
      },
      plot_dendrogram({state}){
        state._dendrogram = false
        fetch(`/plot-dendrogram`, {
          body: JSON.stringify({
            "type_": state.type_
          }),
          method: "POST"
        }).
        then(response => response.json()).
        then(data =>{
          state.dendrogramImage = data.dendrogramImage
          state._dendrogram = true
        })
      },
      plotTwoGenes({state}, params){
        state._plotTwoGenes = false
        fetch('/plot-two-genes',{
          body: JSON.stringify({
            "gene1": /.* ` (.*)$/.exec(state.gene)[1],
            "gene2": /.* ` (.*)$/.exec(params)[1]
          }),
          method: "POST"
        }).
        then(response => response.json()).
        then(data => {
          state.twoGenePlotImage = data.twoGenePlotImage,
          state.twoGenePlotTable = data.twoGenePlotTable,
          state._plotTwoGenes = true
        })
      },
  },
  modules: {
    comparison,
  },
  //First param is state
  getters: {
    genePlotParams(state){
      return {
        gene: state.gene,
        type_: state.type_,
      }
    },
  }
})
