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

    FILE *fp;
    magic_t magic;
    blake2b_state S;
   
    const char *mime;

    unsigned char buf[BUF_SIZE];
    unsigned char magic_buf[BUF_SIZE];
    unsigned char digest[32];
    uint64_t total;
    uint64_t entropy_count[256] = {0};
    
    int rc = 0;
    size_t magic_len;
    size_t n;
    double entropy;

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
    char **paths = argc > 1 ? argv + 1 : dash;

    for (int i = 0; paths[i]; i++) {

        const char *path = paths[i];
        blake2b_init(&S, 32);
        memset(entropy_count, 0, sizeof(entropy_count));
        total = 0;
        magic_len = 0;
        entropy = 0.0;

        fp = strcmp(path, "-") == 0 ? stdin : fopen(path, "rb");
        if (!fp) { perror(path); rc = 1; continue; }

        // read for md5 as well as prepare bytes for file entropy and mime type
        while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
            blake2b_update(&S, buf, n);
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

        blake2b_final(&S, digest, 32);

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

        for (int j = 0; j < 32; j++)
            printf("%02x", digest[j]);

        printf(" %.6f %s  %s\n", entropy, mime, path);
    }

    magic_close(magic);

    return rc;
}
