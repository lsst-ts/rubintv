const path = require('path')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin')

module.exports = {
  mode: 'production',
  devtool: 'source-map',
  entry: {
    style: {
      import: './src/sass/style.sass'
    }
  },
  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, './src/rubintv/static/assets')
  },
  plugins: [new MiniCssExtractPlugin({ filename: '[name].css' })],
  optimization: { minimizer: ['...', new CssMinimizerPlugin()] },
  module: {
    rules: [{
      test: /\.(s[ac]ss|css)$/i,
      use: [
        MiniCssExtractPlugin.loader,
        { loader: 'css-loader', options: { sourceMap: true } },
        { loader: 'postcss-loader', options: { sourceMap: true } },
        { loader: 'sass-loader', options: { sourceMap: true } }
      ]
    }]
  }
}
