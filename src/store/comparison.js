export default {
  state:{
    gene_expression_compare_table: "",
    pvalue_correction_methods: [],
    pvalue_correction_methods_available: false,
  },
  mutations:{},
  actions:{
    gene_expression_compare({state, rootState}, method){
      fetch('/gene-expression-compare',{
        body: JSON.stringify({
          "method": method,
        }),
        method: "POST"
      }).
      then(response => response.json()).
      then(data => {
        state.gene_expression_compare_table = data.gene_expression_compare_table
      })
    },
    get_pvalue_correction_methods({state}){
      fetch('/get-pvalue-correction-methods').
      then(response => response.json()).
      then(data => {
        state.pvalue_correction_methods = data.pvalue_correction_methods
        state.pvalue_correction_methods_available = true
      })
    },
    invalidateColumnsAvailable({state, dispatch}){
      state.gene_expression_compare_table = ""
    }
  },
}
