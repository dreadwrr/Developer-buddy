#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <magic.h>
#include <math.h>
#include <unistd.h>
#include "md5.h"

#define BUF_SIZE 65536
#define MD5_DIGEST_LENGTH 16

/*  Use open wall md5 implementation and also output file shannon entropy  and mime type
    so only have to open the file once 

    if ! ldconfig -p | grep -q libmagic; then
        echo "libmagic missing, exiting"
        exit 1
    fi
    -z end with NUL not newline
            */
int main(int argc, char **argv)
{

    FILE *fp;
    magic_t magic;
    MD5_CTX ctx;
   
    const char *mime;

    unsigned char buf[BUF_SIZE];
    unsigned char magic_buf[BUF_SIZE];
    unsigned char digest[MD5_DIGEST_LENGTH];
    uint64_t total;
    uint64_t entropy_count[256] = {0};
    
    int rc = 0;
    int opt;
    int zero = 0;
    size_t magic_len ;
    size_t n;
    double entropy;

    while ((opt = getopt(argc, argv, "z")) != -1) {
        switch (opt) {
            case 'z':
                zero = 1;
                break;
        }
    }
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

    char *dash[] = { "-", NULL };
    char **paths = argc > 1 ? argv + optind : dash;

    for (int i = 0; paths[i]; i++) {

        const char *path = paths[i];
        MD5_Init(&ctx);
        memset(entropy_count, 0, sizeof(entropy_count));
        total = 0;
        magic_len = 0;
        entropy = 0.0;

        fp = strcmp(path, "-") == 0 ? stdin : fopen(path, "rb");
        if (!fp) { perror(path); rc = 1; continue; }

        // read for md5 as well as prepare bytes for file entropy and mime type
        while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
            MD5_Update(&ctx, buf, n);
            for (size_t j = 0; j < n; j++)
                entropy_count[buf[j]]++;

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
            if (fp != stdin)
                fclose(fp);
            rc = 1;
            continue;
        }

        if (fp != stdin)
            fclose(fp);

        // output area

        MD5_Final(digest, &ctx);

        if (total > 0) {
            for (int j = 0; j < 256; j++) {
                if (entropy_count[j]) {
                    double p = (double)entropy_count[j] / total;
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

        for (int j = 0; j < MD5_DIGEST_LENGTH; j++)
            printf("%02x", digest[j]);

        printf(" %.6f %s  %s%c", entropy, mime, path, zero ? '\0' : '\n');
    }
    
    magic_close(magic);

    return rc;
}
