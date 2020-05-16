<template>
  <b-tab title="Group gene expression comparison">
    <div v-if='pvalue_correction_methods_available'>
      <label>Select multiple tests correction method </label>
      <multiselect
      v-model="method" :options="pvalue_correction_methods" @input="gene_expression_compare(method)">
      </multiselect>
    </div>
    <div  v-html="gene_expression_compare_table"></div>
  </b-tab>
</template>
<script>
import {mapState, mapActions} from 'vuex'
import { Multiselect } from 'vue-multiselect'
export default {
  components: {Multiselect},
  data(){
    return {
      method:''
    }
  },
  computed: {
    ...mapState({
      pvalue_correction_methods: state=> state.comparison.pvalue_correction_methods,
      gene_expression_compare_table: state=> state.comparison.gene_expression_compare_table,
      _subseriesSelected: state=> state._subseriesSelected,
      pvalue_correction_methods_available: state=> state.comparison.pvalue_correction_methods_available,
    })
  },
  methods: {
    ...mapActions([
      'gene_expression_compare', 'get_pvalue_correction_methods'
    ])
  },
  created(){
    this.$store.dispatch('get_pvalue_correction_methods')
  },
}
</script>
