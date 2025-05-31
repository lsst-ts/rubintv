const path = require("path")
const MiniCssExtractPlugin = require("mini-css-extract-plugin")
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin")
const TerserPlugin = require("terser-webpack-plugin")
const { DuplicatesPlugin } = require("inspectpack/plugin")

const pagesWithoutHistory = ["admin", "detectors"].reduce(
  (pages, page) => ({
    ...pages,
    [page]: [`./src/js/pages/${page}.js`],
  }),
  {}
)

const pagesWithHistory = [
  "mosaic-view",
  "night_report",
  "single",
  "camera-table",
  "allsky",
].reduce(
  (pages, page) => ({
    ...pages,
    [page]: [
      `./src/js/pages/${page}.js`,
      "./src/js/modules/ws-service-client.js",
      "./src/js/reload-on-historical.js",
      "./src/js/modules/calendar-controls.js",
    ],
  }),
  {}
)

module.exports = {
  mode: "production",
  devtool: "source-map",
  stats: {
    errorDetails: true,
  },
  entry: {
    style: "./src/sass/style.sass",
    hostbanner: "./src/js/hostbanner.js",
    ...pagesWithoutHistory,
    ...pagesWithHistory,
  },
  output: {
    filename: "[name].js",
    path: path.resolve(__dirname, "assets"),
    chunkFilename: "[name].[chunkhash].js",
  },
  plugins: [
    new MiniCssExtractPlugin({ filename: "[name].css" }),
    new DuplicatesPlugin({
      emitErrors: false,
      verbose: false,
    }),
  ],
  optimization: {
    minimizer: ["...", new TerserPlugin(), new CssMinimizerPlugin()],
    splitChunks: {
      chunks: "all",
      minSize: 20000,
      minChunks: 1,
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: "vendors",
          chunks: "all",
        },
        common: {
          name: "common",
          minChunks: 2,
          chunks: "all",
          priority: -20,
          reuseExistingChunk: true,
        },
      },
    },
  },
  resolve: {
    extensions: [".js", ".jsx", ".ts", ".tsx"],
    modules: [path.resolve(__dirname, "src"), "node_modules"],
  },
  module: {
    rules: [
      {
        test: /\.(s[ac]ss|css)$/i,
        use: [
          MiniCssExtractPlugin.loader,
          { loader: "css-loader", options: { sourceMap: true } },
          { loader: "postcss-loader", options: { sourceMap: true } },
          { loader: "sass-loader", options: { sourceMap: true } },
        ],
      },
      {
        test: /\.(js|jsx|ts|tsx)$/,
        exclude: /node_modules/,
        use: {
          loader: "ts-loader",
          options: {
            transpileOnly: true,
            compilerOptions: {
              module: "es6",
              allowSyntheticDefaultImports: true,
            },
          },
        },
      },
    ],
  },
}
