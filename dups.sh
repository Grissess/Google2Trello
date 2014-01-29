cat G2T_LOG | grep WARNING | cut -d " " -f 6- | tr "\n" ";" && echo
