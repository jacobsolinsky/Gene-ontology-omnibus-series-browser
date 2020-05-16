<template>
  <div>
    <b-button v-b-toggle.select-sample-columns variant="primary">Select Sample Columns</b-button>
    <b-collapse visible id='select-sample-columns'>
    <b-button @click="showExcel=!showExcel">
      {{ !showExcel ? 'Show beginning of column data': 'Hide beginning of column data'}}
    </b-button>
      <table>
        <tr class="flex-row">
          <td class="sample" :class="{'sample-gene-id':sample.gene & sample.id
          ,'sample-id':sample.id, 'sample-gene':sample.gene, 'sample-checked': sample.checked}" v-for="(sample, index) in excelColumns">
            <h6>{{index}}</h6>
            <label style="display:inline;">Group:</label>
            <input type="text" style="display:inline; width: 10em;" v-model="sample.group"
              @input="updateText($event, index, sample)">
              <ol :class="{'excel-visible': showExcel, 'excel-invisible': !showExcel}">
                <li v-for="i in sample.values">{{i}}</li>
              </ol>
            <div v-if="gene_id_needed">
              <label>Column contains Gene IDs?</label>
                <input type="checkbox" v-model="sample.id" @input="updateId($event, index, sample)"></input>
              <label>Column contains Gene Symbols?</label>
                <input type="checkbox" v-model="sample.gene" @input="updateGene($event, index, sample)"></input>
            </div>
          </td>
        </tr>
      </table>
    </b-collapse>
  </div>
</template>
<script>
import {mapState, mapActions} from 'vuex'
export default{
  data(){
    return {showExcel:true}
  },
  computed:{
    ...mapState(['excelColumns', 'gene_id_needed']),
    excelColumns:{
      set(a) {this.$store.commit('setExcelColumns', a)},
      get(){return this.$store.state.excelColumns},
    },
  },
  methods:{
    ...mapActions(['set_sample_columns']),
    updateText(e, i, sample){
      this.excelColumns[i].group = e.target.value
      this.set_sample_columns()
    },
    updateId(e, i, sample){
      this.excelColumns[i].id = e.target.checked
      this.set_sample_columns()
    },
    updateGene(e, i, sample){
      this.excelColumns[i].gene = e.target.checked
      this.set_sample_columns()
    },
  },

}
</script>
<style>
.flex-row{
  width: 90vw;
  display: flex;
  justify-content: left;
  flex-wrap: wrap;
}
.sample{
  box-shadow:
    0 1px 2px #fff, /*bottom external highlight*/
    0 -1px 1px #666, /*top external shadow*/
    inset 0 -1px 1px rgba(0,0,0,0.5), /*bottom internal shadow*/
    inset 0 1px 1px rgba(255,255,255,0.8); /*top internal highlight*/
}
.sample-checked {
  background-color: #90ee90;
}
.sample-id {
  background-color: yellow;
}
.sample-gene {
  background-color: pink;
}
.sample-gene-id {
  background: repeating-linear-gradient(
    45deg,
    #yellow,
    #yellow 10px,
    #pink 10px,
    #pink 20px
  )
}
.excel-visible{display: block;}
.excel-invisible{display: none;}
</style>
