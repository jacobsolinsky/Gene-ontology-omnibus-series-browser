const VueLoaderPlugin = require('vue-loader/lib/plugin');
var path = require('path')
module.exports = {
  entry: './src/main.js',
  mode:'development',
  output: {
    filename: 'app.js',
    path: path.join(__dirname, 'dist/js')
  },
  module: {
    rules: [
      { test: /\.js$/, use: 'babel-loader' },
      { test: /\.vue$/, use: 'vue-loader' },
      { test: /\.css$/, use: ['vue-style-loader', 'css-loader']},
    ]
  },
  plugins: [
    new VueLoaderPlugin(),
  ]
};
