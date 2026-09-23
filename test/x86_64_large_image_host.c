#include <reist/x86_64/image.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern int __attribute__((sysv_abi)) boot_program_admit64(const void *,size_t);
static int admission(unsigned char *record,unsigned bytes) {
    if(boot_program_admit64(record,bytes)!=1)return 1;
    if(bytes!=REIST_X64_PREPARED_V3_BYTES)return 0;
    for(unsigned page=0;page<256;page++) {
        unsigned char old=record[24+page];record[24+page]=7;
        int result=boot_program_admit64(record,bytes);record[24+page]=old;
        if(result!=0)return 2;
    }
    record[280]=1;int result=boot_program_admit64(record,bytes);record[280]=0;
    if(result!=0)return 3;
    record[288+7*4096]=1;result=boot_program_admit64(record,bytes);record[288+7*4096]=0;
    if(result!=0)return 4;
    return boot_program_admit64(record,bytes-1)!=0;
}
int main(int argc,char **argv) {
    if(argc!=4)return 90;
    FILE *f=fopen(argv[2],"rb");if(!f)return 91;
    if(fseek(f,0,SEEK_END))return 92;long size=ftell(f);
    if(size<0||size>2097152||fseek(f,0,SEEK_SET))return 93;
    unsigned char *input=malloc((size_t)size+1),*out=malloc(REIST_X64_PREPARED_V3_BYTES);
    if(!input||!out||fread(input,1,(size_t)size,f)!=(size_t)size||fclose(f))return 94;
    memset(out,0xa5,REIST_X64_PREPARED_V3_BYTES);
    int status=argv[1][0]=='3'?reist_x64_image_prepare_v3(out,input,(size_t)size):
        reist_x64_image_prepare_v2(out,input,(size_t)size);
    if(status){for(unsigned i=0;i<REIST_X64_PREPARED_V3_BYTES;i++)if(out[i]!=0xa5)return 95;return status==-22?22:96;}
    f=fopen(argv[3],"wb");if(!f)return 97;
    unsigned n=argv[1][0]=='3'?REIST_X64_PREPARED_V3_BYTES:REIST_X64_PREPARED_V2_BYTES;
    if(admission(out,n))return 99;
    if(fwrite(out,1,n,f)!=n||fclose(f))return 98;
    free(input);free(out);return 0;
}
