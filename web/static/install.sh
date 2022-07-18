#!/bin/sh
# author: @Zeecka_
# Usage: aperisolve <file>

cat << EOF > /usr/bin/aperisolve
HOST="https://www.aperisolve.com"
ARGC=\$#
EXPECTED_ARGS=1

if [ \$# -eq \$EXPECTED_ARGS ]
then
    P=$(realpath \$1) # Get File Path Browser
    REPHASH=$(curl -s -F file=@\$P \$HOST/upload | jq .File | tr -d '"') # Upload and get hash
    xdg-open \$HOST/\$REPHASH  # Open Browser
else
    echo "[?] Usage: aperisolve <file>"
fi;
EOF
chmod +x /usr/bin/aperisolve
echo "Aperi'Solve 🍉 is installed (/usr/bin/aperisolve) 🙂."
echo "Usage: aperisolve <file>"