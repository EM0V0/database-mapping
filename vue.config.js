// vue.config.js
module.exports = {
  devServer: {
    // Forward same-origin `/api/*` requests to Flask without rewriting prefixes.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
};
