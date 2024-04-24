#!/usr/bin/env bash
#test wheels in different directory
set -e
set -x
package=$1

FILE_PATH="`dirname \"$0\"`"
FILE_PATH="`( cd \"$FILE_PATH\" && pwd )`"
if [ -z "$FILE_PATH" ] ; then
  exit 1
fi

cd $TMP
cp -r $package/tests mtests
export HYPOTHESIS_PROFILE=fast
pytest --stepwise-skip mtests
rm -r mtests
cd $FILE_PATH
