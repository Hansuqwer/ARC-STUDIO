import re

with open('gen-webpack.config.js', 'r') as f:
    content = f.read()

# Pattern to match the problematic alias section
pattern = r"alias: \{\s*// Replace Monaco's nls module with Theia's localization-aware version\.\s*// ESM exports are immutable[^\}]*\[path\.join\(resolvePackagePath\('@theia/monaco-editor-core', __dirname\)[^\}]*\}"

replacement = """alias: (() => {
            // Replace Monaco's nls module with Theia's localization-aware version.
            const monacoEditorCore = resolvePackagePath('@theia/monaco-editor-core', __dirname);
            const monaco = resolvePackagePath('@theia/monaco', __dirname);
            if (monacoEditorCore && monaco) {
                return {
                    [path.join(monacoEditorCore, '..', 'esm', 'vs', 'nls.js')]:
                        path.join(monaco, '..', 'lib', 'browser', 'monaco-nls.js')
                };
            }
            return {};
        })()"""

# Replace all occurrences
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('gen-webpack.config.js', 'w') as f:
    f.write(content)

print('Fixed webpack config')
