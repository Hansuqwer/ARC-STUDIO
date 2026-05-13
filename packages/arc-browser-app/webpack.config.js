/**
 * This file can be edited to customize webpack configuration.
 * To reset delete this file and rerun theia build again.
 */
// @ts-check
const fs = require('fs');
const path = require('path');
const configs = require('./gen-webpack.config.js');
const nodeConfig = require('./gen-webpack.node.config.js');

const isProduction = process.env.NODE_ENV === 'production';

/**
 * Expose bundled modules on window.theia.moduleName namespace, e.g.
 * window['theia']['@theia/core/lib/common/uri'].
 * Such syntax can be used by external code, for instance, for testing.
configs[0].module.rules.push({
    test: /\.js$/,
    loader: require.resolve('@theia/application-manager/lib/expose-loader')
}); */

// Apply production optimizations
for (const config of configs) {
    if (isProduction) {
        config.devtool = false;
    }
}

// Add stats generation plugin to frontend config (skip in production to save space)
if (configs.length > 0) {
    const frontendConfig = configs[0];
    const originalPlugins = frontendConfig.plugins || [];
    
    if (!isProduction) {
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
    }

    // Enable performance hints
    frontendConfig.performance = {
        hints: 'warning',
        maxEntrypointSize: 10 * 1024 * 1024,
        maxAssetSize: 10 * 1024 * 1024
    };
}

// Add plugin to remove source maps and unnecessary files in production
if (isProduction) {
    for (const config of configs) {
        const originalPlugins = config.plugins || [];
        config.plugins = [
            ...originalPlugins,
            {
                apply: (compiler) => {
                    compiler.hooks.afterEmit.tapPromise('RemoveSourceMapsPlugin', async (compilation) => {
                        const outputPath = compilation.outputOptions.path;
                        const glob = require('glob');
                        let removedCount = 0;
                        
                        const mapFiles = glob.sync(path.join(outputPath, '**/*.map'));
                        for (const file of mapFiles) {
                            try { fs.unlinkSync(file); removedCount++; } catch (e) {}
                        }
                        
                        const mapGzFiles = glob.sync(path.join(outputPath, '**/*.map.gz'));
                        for (const file of mapGzFiles) {
                            try { fs.unlinkSync(file); removedCount++; } catch (e) {}
                        }
                        
                        const statsFiles = glob.sync(path.join(outputPath, '**/stats.json'));
                        for (const file of statsFiles) {
                            try { fs.unlinkSync(file); removedCount++; } catch (e) {}
                        }
                        
                        if (removedCount > 0) {
                            console.log(`[ARC] Production cleanup: removed ${removedCount} files (source maps, compressed maps, stats)`);
                        }
                    });
                }
            }
        ];
    }
}

module.exports = [
    ...configs,
    nodeConfig.config
];
