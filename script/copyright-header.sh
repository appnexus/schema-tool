#!/bin/bash

##-----------------------------------------------------------------
## Open source demands copyright headers. But it sucks to keep
## these up to date manually. This script just offers us an easy
## way to make sure they're all up to date.
##-----------------------------------------------------------------

read -r -d '' COPYRIGHT <<'EOF'
// <--
// Copyright © 2017 AppNexus Inc.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// -->
EOF
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COPYRIGHT_FILE="${DIR}/copyright.txt"

# write copyright file in script dir
echo "$COPYRIGHT" > "${COPYRIGHT_FILE}"

# switch to top-level dir of project
cd "${DIR}/.."

# Write to main license file to keep it in sync (this script is the source of
# truth for the license and should be changed here if changed at all)
echo "$COPYRIGHT" \
    | awk -v m=1 -v n=1 'NR<=m{next};NR>n+m{print line[NR%n]};{line[NR%n]=$0}' \
    | sed 's/^\/\/[[:space:]]\{0,1\}//g' >LICENSE

# Because we don't want our copyright toever be out of date,
# let's just update all of the files, replacing any existing
# copyright.
for file in $(find . | grep '\.go$' | grep -v vendor) ; do
  start=$(grep -n '^// <--$' $file | awk -F':' '{print $1}')
  end=$(grep -n '^// -->$' $file | awk -F':' '{print $1}')
  if [ "$start" != "" ] && [ $start -ne 0 ] ; then
    if [ "$end" != "" ] && [ $end -ne 0 ] && [ $end -gt $start ]; then
      # delete old license (rewrite every time to keep it in sync)
      # some OSs (Mac) require an extension to -i, create a backup and then rm it
      sed -ibak -e "${start},${end}d" $file
      rm "${file}bak"
    fi
  fi

  # add copyright header
  cat "${COPYRIGHT_FILE}" "$file" > "${file}.bak"
  mv "${file}.bak" "$file"
done

rm "${COPYRIGHT_FILE}"
