/**
 * This file can be edited to customize webpack configuration.
 * To reset delete this file and rerun theia build again.
 */
// @ts-check
const fs = require('fs');
const path = require('path');
const configs = require('./gen-webpack.config.js');
const nodeConfig = require('./gen-webpack.node.config.js');

/**
 * Expose bundled modules on window.theia.moduleName namespace, e.g.
 * window['theia']['@theia/core/lib/common/uri'].
 * Such syntax can be used by external code, for instance, for testing.
configs[0].module.rules.push({
    test: /\.js$/,
    loader: require.resolve('@theia/application-manager/lib/expose-loader')
}); */

// Add stats generation plugin to frontend config
if (configs.length > 0) {
    const frontendConfig = configs[0];
    const originalPlugins = frontendConfig.plugins || [];
    
    frontendConfig.plugins = [
        ...originalPlugins,
        {
            apply: (compiler) => {
                compiler.hooks.done.tap('StatsJsonPlugin', (stats) => {
                    const statsPath = path.join(compiler.outputPath, 'stats.json');
                    const statsJson = stats.toJson({
                        all: true,
                        modules: true,
                        chunks: true,
                        timings: true,
                        colors: true,
                        performance: true
                    });
                    fs.writeFileSync(statsPath, JSON.stringify(statsJson, null, 2));
                    console.log(`[ARC] Stats written to: ${statsPath}`);
                });
            }
        }
    ];

    // Enable performance hints
    frontendConfig.performance = {
        hints: 'warning',
        maxEntrypointSize: 10 * 1024 * 1024,
        maxAssetSize: 10 * 1024 * 1024
    };
}

module.exports = [
    ...configs,
    nodeConfig.config
];
