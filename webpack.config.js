const path = require('path')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin')
const TerserPlugin = require('terser-webpack-plugin')

const pagesWithHeartbeats = [
  'auxtel',
  'startracker',
  'admin'
].reduce((pages, page) => ({
  ...pages, [page]: [`./src/js/pages/${page}.js`, './src/js/heartbeats.js']
}), {})

const pagesWithout = [
  'current',
  'allsky_historical',
  'auxtel_historical',
  'startracker_historical',
  'night_report',
  'night_report_historical'
].reduce((pages, page) => ({
  ...pages, [page]: `./src/js/pages/${page}.js`
}), {})

module.exports = {
  mode: 'production',
  devtool: 'source-map',
  entry: {
    style: './src/sass/style.sass',
    hostbanner: './src/js/hostbanner.js',
    ...pagesWithHeartbeats,
    ...pagesWithout
  },
  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, './src/rubintv/static/assets')
  },
  plugins: [new MiniCssExtractPlugin({ filename: '[name].css' })],
  optimization: {
    minimizer: [
      '...',
      new TerserPlugin(),
      new CssMinimizerPlugin()
    ]
  },
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
