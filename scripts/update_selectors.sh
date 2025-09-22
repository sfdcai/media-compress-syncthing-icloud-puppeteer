#!/bin/bash

# Selector Update Helper Script
# This script helps you update iCloud Photos selectors when Apple changes their interface

echo "=== iCloud Photos Selector Update Helper ==="
echo ""

# Check if test results exist
if [ -f "selector_test_results.json" ]; then
    echo "Found previous test results:"
    cat selector_test_results.json | jq '.workingSelectors[]' 2>/dev/null || cat selector_test_results.json
    echo ""
fi

echo "To update selectors:"
echo "1. Run the selector testing script:"
echo "   node scripts/test_selectors.js"
echo ""
echo "2. The script will open a browser and test all selectors"
echo "3. Check the results in selector_test_results.json"
echo "4. Update scripts/icloud_selectors.json with new selectors"
echo "5. Test the updated selectors:"
echo "   node scripts/upload_icloud.js --dir /tmp/test_upload"
echo ""
echo "Current selectors file:"
echo "scripts/icloud_selectors.json"
echo ""
echo "To edit selectors:"
echo "nano scripts/icloud_selectors.json"
echo ""
echo "To test current selectors:"
echo "node scripts/upload_icloud.js --dir /tmp/test_upload"
