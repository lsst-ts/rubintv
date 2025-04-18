const path = require("path")
const MiniCssExtractPlugin = require("mini-css-extract-plugin")
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin")
const TerserPlugin = require("terser-webpack-plugin")
const { DuplicatesPlugin } = require("inspectpack/plugin")

const pagesWithoutHistory = ["admin"].reduce(
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
  },
  plugins: [
    new MiniCssExtractPlugin({ filename: "[name].css" }),
    new DuplicatesPlugin({
      // Emit compilation warning or error? (Default: `false`)
      emitErrors: false,
      // Display full duplicates information? (Default: `false`)
      verbose: false,
    }),
  ],
  optimization: {
    minimizer: ["...", new TerserPlugin(), new CssMinimizerPlugin()],
  },
  resolve: {
    extensions: [".js", ".jsx"],
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
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
        },
      },
    ],
  },
}
