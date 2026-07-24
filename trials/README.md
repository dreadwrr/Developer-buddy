# b2ent

Single-pass file analyzer that outputs:
- blake2b 256 checksum
- Shannon entropy
- MIME type

## Build

Requires:
- libmagic development package

Compile:

    gcc -O2 -o b2ent b2ent.c blake2b-ref.c -lmagic -lm
    gcc -O2 -o md5ent md5.c md5ent.c -lmagic -lm
Run:

    ./b2ent filename
    ./md5ent filename
