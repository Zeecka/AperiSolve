#!/bin/sh
# author: @Zeecka_
# Modified for macOS by Eric Pan
# Usage: aperisolve <file>

unameOut="$(uname -s)"
case "${unameOut}" in
    Darwin*)    echo 'Installing for macOS...' && cat << EOF > /usr/local/bin/aperisolve
HOST="https://www.aperisolve.com"
ARGC=\$#
EXPECTED_ARGS=1

if [ \$# -eq \$EXPECTED_ARGS ]
then
    P=\$(realpath \$1) # Get File Path Browser
    REPHASH=\$(curl -s -F file=@\$P \$HOST/upload | jq .File | tr -d '"') # Upload and get hash
    xdg-open \$HOST/\$REPHASH  # Open Browser
else
    echo "[?] Usage: aperisolve <file>"
fi;
EOF
chmod +x /usr/local/bin/aperisolve
echo "Aperi'Solve 🍉 is installed (/usr/local/bin/aperisolve) 🙂."
echo "Usage: aperisolve <file>";;
    *)          echo 'Installing for Linux...' && cat << EOF > /usr/bin/aperisolve
HOST="https://www.aperisolve.com"
ARGC=\$#
EXPECTED_ARGS=1

if [ \$# -eq \$EXPECTED_ARGS ]
then
    P=\$(realpath \$1) # Get File Path Browser
    REPHASH=\$(curl -s -F file=@\$P \$HOST/upload | jq .File | tr -d '"') # Upload and get hash
    xdg-open \$HOST/\$REPHASH  # Open Browser
else
    echo "[?] Usage: aperisolve <file>"
fi;
EOF
chmod +x /usr/bin/aperisolve
echo "Aperi'Solve 🍉 is installed (/usr/bin/aperisolve) 🙂."
echo "Usage: aperisolve <file>";;
esac
