<template>
  <div>
    <textarea style='width: 80em; height: 10em;' readonly>{{past_text}}</textarea>
    <textarea style="width: 80em; height: 20em;" v-model='input_text'></textarea>
    <button @click='submit'>Submit</button>
    <span>{{output}}</span>
  </div>
</template>
<script>
export default {
  data(){
    return {
      past_text: '',
      input_text: '',
      output: '',
    }
  },
  methods:{
    submit(){
      this.past_text += `\n${this.input_text}`
      fetch('/commandline', {
        body: this.input_text,
        method: 'POST',
        }
      ).
        then(response => response.text()).
        then(data => this.output = data)
    }
  },
}
</script>
