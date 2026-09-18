/* Production enumerators extracted byte-exactly; model only DRIVE_INFO. */
#ifdef NDEBUG
#error "Drive behavior tests require active assertions"
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <x86os.h>
static int behavior,calls;
int x86os_drive_info(uint32_t index,x86os_drive_info_t *out) {
    ++calls;assert(calls<=33);
    if(behavior==0)return -38;
    if(behavior==1)return 0;
    if(behavior==5)return 2;
    if(behavior==6 && index==1)return -5;
    if(behavior!=4 && index==2)return 0;
    memset(out,0,sizeof(*out));out->type=X86OS_DRIVE_ATA;
    strcpy(out->name,index==0?"ata0":"ata1");
    strcpy(out->mount_point,index==0?"/":"/data");
    return 1;
}
#include "shell_drive_functions.h"
int main(void) {
    x86os_drive_info_t out,before;memset(&before,0xa5,sizeof(before));
    for(int b=0;b<=6;++b) {
        if(b==2 || b==3)continue;
        behavior=b;calls=0;out=before;
        assert(find_drive('Z',&out)==-1 && !memcmp(&out,&before,sizeof(out)));
        assert(calls==(b==4?32:b==6?2:1));
        calls=0;out=before;
        assert(current_drive("/data/file",&out)==-1 && !memcmp(&out,&before,sizeof(out)));
        assert(calls==(b==4?32:b==6?2:1));
    }
    behavior=2;calls=0;
    assert(find_drive('c',&out)==0 && calls==1 && !strcmp(out.mount_point,"/"));
    calls=0;assert(find_drive('D',&out)==0 && calls==2 && !strcmp(out.mount_point,"/data"));
    calls=0;assert(current_drive("/data/file",&out)==0 && calls==3 && !strcmp(out.mount_point,"/data"));
    calls=0;assert(current_drive("/database",&out)==0 && calls==3 && !strcmp(out.mount_point,"/"));
    puts("SHELL_DRIVES_HOST_OK");return 0;
}
