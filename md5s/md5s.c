#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "md5.h"

#define BUF_SIZE 65536
#define MD5_DIGEST_LENGTH 16

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <file>\n", argv[0]);
        return 1;
    }

    FILE *fp = fopen(argv[1], "rb");
    if (!fp) {
        perror("fopen");  // fprintf(stderr, "fopen: %s\n", strerror(errno));
        return 1;
    }

    MD5_CTX ctx;
    unsigned char digest[MD5_DIGEST_LENGTH];

    unsigned char buf[BUF_SIZE];
    uint64_t entropy_count[256] = {0};
    uint64_t total = 0;
    double entropy = 0.0;
    size_t n;

    MD5_Init(&ctx);

    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        MD5_Update(&ctx, buf, n);
        for (size_t i = 0; i < n; i++)
            entropy_count[buf[i]]++;

        total += n;
    }

    if (ferror(fp)) {
        perror("fread");
        fclose(fp);
        return 1;
    }

    fclose(fp);

    for (int i = 0; i < 256; i++) {
        if (entropy_count[i]) {
            double p = (double)entropy_count[i] / total;
            entropy -= p * log2(p);
        }
    }

    MD5_Final(digest, &ctx);

    for (int i = 0; i < MD5_DIGEST_LENGTH; i++)
        printf("%02x", digest[i]);

    printf(" %.6f\n", entropy);

    return 0;
}
