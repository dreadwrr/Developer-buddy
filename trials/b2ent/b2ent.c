#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <magic.h>
#include <math.h>
#include "blake2.h"

#define BUF_SIZE 65536

/*  Use blake2b implementation and also output file shannon entropy  and mime type
    so only have to open the file once 

    if ! ldconfig -p | grep -q libmagic; then
        echo "libmagic missing, exiting"
        exit 1
    fi
    
            */
int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <file>\n", argv[0]);
        return 1;
    }

    FILE *fp;
    magic_t magic;
    blake2b_state S;
   
    const char *mime;

    unsigned char buf[BUF_SIZE];
    unsigned char magic_buf[BUF_SIZE];
    unsigned char digest[32];
    uint64_t total = 0;
    uint64_t entropy_count[256] = {0};
    size_t magic_len = 0;
    size_t n;
    double entropy = 0.0;

    magic = magic_open(MAGIC_MIME_TYPE);
    if (!magic) {
        fprintf(stderr, "magic_open failed\n");
        return 1;
    }
    if (magic_load(magic, NULL) != 0) {
        fprintf(stderr, "%s\n", magic_error(magic));
        magic_close(magic);
        return 1;
    }

    fp = fopen(argv[1], "rb");
    if (!fp) {
        perror("fopen");  // fprintf(stderr, "fopen: %s\n", strerror(errno));
        magic_close(magic);
        return 1;
    }

    blake2b_init(&S, 32);
    if (blake2b_init(&S, 32) != 0) {
        fprintf(stderr, "blake2b_init failed\n");
        fclose(fp);
        magic_close(magic);
        return 1;
    }

    // read for md5 as well as prepare bytes for file entropy and mime type
    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        blake2b_update(&S, buf, n);
        for (size_t i = 0; i < n; i++)
            entropy_count[buf[i]]++;

        if (magic_len < sizeof(magic_buf)) {
            size_t copy = n;
            size_t held = sizeof(magic_buf) - magic_len;

            if (copy > held)
                copy = held;

            memcpy(magic_buf + magic_len, buf, copy);
            magic_len += copy;
        }
        total += n;
    }

    if (ferror(fp)) {
        perror("fread");
        fclose(fp);
        magic_close(magic);
        return 1;
    }

    fclose(fp);

    // output area

    blake2b_final(&S, digest, 32);

    if (total > 0) {
        for (int i = 0; i < 256; i++) {
            if (entropy_count[i]) {
                double p = (double)entropy_count[i] / total;
                entropy -= p * log2(p);
            }
        }
    }

    mime = magic_buffer(magic, magic_buf, magic_len);
    if (!mime) {
        fprintf(stderr, "magic_buffer failed: %s\n", magic_error(magic));
        // magic_close(magic);
        // return 1;
        mime = "None";
    } 
    // else if (strcmp(mime, "application/octet-stream") == 0) {
        // mime = "Unknown";
    // }

    for (int i = 0; i < 32; i++)
        printf("%02x", digest[i]);

    printf(" %.6f %s\n", entropy, mime);
    
    magic_close(magic);

    return 0;
}
