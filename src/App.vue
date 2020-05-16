<template>
  <div class="container">
    <div class="column-1">
      <button @click.stop.prevent="download_gse(gse_accession_id)">Download GSE</button>
      <input @keyup.enter="download_gse(gse_accession_id)" type="text" v-model="gse_accession_id">

      <div v-if="_gseDownloading">GSE Downloading</div>
      <div v-if="_error">{{error}}</div>

      <div v-if="_gseDownloaded">
      <label> Select platform ID (most datasets have only one, but some have multiple)</label>
      <multiselect
      v-model="subseriesId" :options="subseries" @input="select_subseries(subseriesId)">
      </multiselect>
      </div>

      <geneplot v-if="_subseriesSelected"></geneplot>

      <b-tabs v-if="_subseriesSelected">
        <b-tab title="Sample Dendrogram" @click.stop.prevent="plot_dendrogram">
          <div v-if="_dendrogram" v-html="dendrogramImage"></div>
        </b-tab>
        <b-tab v-if="_genePlot" title="Gene Expression Plot">
          <div  v-html="genePlotImage"></div>
        </b-tab>
        <b-tab v-if="_genePlot" title="Gene Expression Table">
          <div  v-html="genePlotTable"></div>
        </b-tab>
        <b-tab v-if="_genePlot" title="Gene Correlation Table">
          <b-table  :items="geneCorrelationTable" @row-clicked="plotTwoGenes"></b-table>
          <div v-if="_plotTwoGenes" v-html="twoGenePlotImage"></div>
          <div v-if="_plotTwoGenes" v-html="twoGenePlotTable"></div>
        </b-tab>
        <b-tab v-if="_genePlot" title="Interactive CommandLine">
          <commandline></commandline>
        </b-tab>
        <comparison v-if="_subseriesSelected"></comparison>
      </b-tabs>
    </div>
    <div class="column-2">
      <iframe style="width:100%; height:100%;" v-if="_gseDownloaded" :src="`https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${gse_accession_id}`"></iframe>
    </div>
  </div>

</template>
<script>
  import { mapState, mapActions } from 'vuex'
  import geneplot from './components/geneplot.vue'
  import comparison from './components/comparison.vue'
  import commandline from './components/commandline.vue'
  import {Multiselect} from 'vue-multiselect'
  export default {
    components: {geneplot, Multiselect, comparison, commandline},
    data(){
      return { gse_accession_id: ""}
    },
    computed: {
      ...mapState(
        ['_error', 'error', '_gseDownloaded', '_gseDownloading', '_subseriesSelected',
      '_selectSampleColumns',
          '_dendrogram', 'dendrogramImage', 'subseries', 'subseriesId',
          '_genePlot', 'genePlotImage', 'genePlotTable', 'geneCorrelationTable',
        '_plotTwoGenes', 'twoGenePlotImage', 'twoGenePlotTable']
      ),
      subseriesId:{
        set(a) {this.$store.commit('setSubseriesId', a)},
        get(){return this.$store.state.subseriesId},
      },
  },
  methods : {
    ...mapActions([
      'download_gse', 'select_subseries',
      'plot_dendrogram', 'plot-two-genes'
    ]),
    plotTwoGenes(record, index){
      this.$store.dispatch('plotTwoGenes', record.gene)
    },
  }

 }
</script>


<style>
.container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  height: 100%;
  width: 90%;
}
.column-1 {
  grid-column: 1;
  height: 100%;
}
.column-2 {
  grid-column: 2;
  height: 100%;
}
</style>
