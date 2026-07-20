#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <magic.h>
#include <math.h>
#include "md5.h"

#define BUF_SIZE 65536
#define MD5_DIGEST_LENGTH 16

/*  Use open wall md5 implementation and also output file shannon entropy  and mime type
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
    MD5_CTX ctx;
   
    const char *mime;

    unsigned char buf[BUF_SIZE];
    unsigned char magic_buf[BUF_SIZE];
    unsigned char digest[MD5_DIGEST_LENGTH];
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

    MD5_Init(&ctx);

    // read for md5 as well as prepare bytes for file entropy and mime type
    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        MD5_Update(&ctx, buf, n);
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

    MD5_Final(digest, &ctx);

    if (total > 0) {
        for (int i = 0; i < 256; i++) {
            if (entropy_count[i]) {
                double p = (double)entropy_count[i] / total;
                entropy -= p * log2(p);
            }
        }
    }

    mime = magic_buffer(magic, magic_buf, magic_len);
    
    if (!mime)
        mime = "Unknown";  // default value "application/octet-stream";

    for (int i = 0; i < MD5_DIGEST_LENGTH; i++)
        printf("%02x", digest[i]);

    printf(" %.6f %s\n", entropy, mime);
    
    magic_close(magic);

    return 0;
}
