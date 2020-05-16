<template>
  <div display style="border: solid;">
    <sampleannotator></sampleannotator>
    <div>
      <label style="font-style: italic; display: inline;">Select gene</label>
      <multiselect style="display: inline;"
      v-model="gene" :options="genes" @input="updateGenePlotParams()">
      </multiselect>

      <label style="font-style: italic; display: inline;">Select normalization type</label>
      <multiselect style="display: inline;"
      v-model="type_" :options="type_s" @input="updateGenePlotParams()">
      </multiselect>
    </div>
  </div>
</template>
<script>
import Multiselect from 'vue-multiselect'
import sampleannotator from './sampleannotator.vue'
import {mapState, mapActions} from 'vuex'
export default {
  components: {Multiselect, sampleannotator},
  data(){
    return {
      thisSampleColumns: []
    }
  },
  computed: {
    ...mapState(
      ['genes', 'gene', 'type_s', 'type']
    ),
    gene:{
      set(a) {this.$store.commit('setGene', a)},
      get(){return this.$store.state.gene},
    },
    type_:{
      set(a) {this.$store.commit('setType_', a)},
      get(){return this.$store.state.type_},
    },
  },
  methods: {
    ...mapActions([
      'updateGenePlotParams',
    ]),
    geneId(g){
      return `${g.gene} \` ${g.id}`
    }
  }
}
</script>
<style>
.multiselect__content-wrapper {
  /*position:absolute;*/
  display: block;
  background: #fff;
  width: 100%;
  max-height: 240px;
  overflow: auto;
  border: 1px solid #e8e8e8;
  border-top: none;
  border-bottom-left-radius: 5px;
  border-bottom-right-radius: 5px;
  z-index: 50;
  -webkit-overflow-scrolling: touch
}
</style>
