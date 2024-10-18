#!/bin/bash
scriptDir=$(realpath $(dirname $0))
baseDir=$(basename $scriptDir)
zipName="${baseDir}.zip"
echo "Zipping to ${zipName}"
cd ../
parentDir=$(pwd)
zip -r6 $zipName $baseDir  -x="*__pycache__*" -x="*.git*" -x="*.idea*"  -x="*DS_Store*" -x "*.files*" -x "*makezip.sh*"
cd -
echo "----------------------------------------------------------------"
echo "Zipped to $parentDir/${zipName}"
echo "----------------------------------------------------------------"
