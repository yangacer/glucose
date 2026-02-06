#!/bin/bash
# Validation script for static files refactoring

echo "Validating static files structure..."

# Check directory structure
if [ ! -d "static/css" ]; then
    echo "ERROR: css directory missing"
    exit 1
fi

if [ ! -d "static/js" ]; then
    echo "ERROR: js directory missing"
    exit 1
fi

# Check CSS file
if [ ! -f "static/css/styles.css" ]; then
    echo "ERROR: styles.css missing from css directory"
    exit 1
fi

# Check JS modules
JS_FILES="config.js utils.js tabs.js dashboard.js data-loader.js dynamic-items.js forms.js audit.js main.js"
for file in $JS_FILES; do
    if [ ! -f "static/js/$file" ]; then
        echo "ERROR: $file missing from js directory"
        exit 1
    fi
done

# Check index.html references
if ! grep -q 'href="css/styles.css"' static/index.html; then
    echo "ERROR: index.html does not reference css/styles.css"
    exit 1
fi

if ! grep -q 'src="js/config.js"' static/index.html; then
    echo "ERROR: index.html does not reference js modules"
    exit 1
fi

# Check that old app.js is backed up
if [ ! -f "static/app.js.backup" ]; then
    echo "WARNING: app.js.backup not found"
fi

echo "✓ All structure checks passed"
echo "✓ CSS file in correct location"
echo "✓ All JS modules present"
echo "✓ index.html references updated"
echo ""
echo "Static files refactoring validated successfully!"
