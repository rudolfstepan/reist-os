"""Execute the actual native user-access core and the old image-selector defect."""
from pathlib import Path
import subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'test'))
sys.path.insert(0,str(ROOT/'scripts'))
import test_x86_64_task_frames as host_builder

class UserAccessTests(unittest.TestCase):
    def test_legacy_selected_image_mismatch(self):
        old=subprocess.check_output(['git','show','1aabfd50:arch/x86_64/proc/cooperative_scheduler.asm'],cwd=ROOT,text=True,timeout=10)
        body='scheduler_validate_shell_range64:'+old.split('scheduler_validate_shell_range64:',1)[1].split('scheduler_validate_shell_ipc_endpoint64:',1)[0]
        asm='''BITS 64
USER_BASE equ 0x400000
USER_END equ 0x408000
USER_STACK_BASE equ 0x408000
USER_STACK_TOP equ 0x409000
TASK_STATE equ 0
TASK_STACK_FRAME equ 24
TASK_RUNNING equ 2
section .bss
scheduler_current_slot: resd 1
scheduler_tasks: resq 128
section .text
global legacy_access
legacy_access:
    push r12
    push r14
    mov rax, rdi
    mov edx, 140
    mov ecx, 4
    call scheduler_validate_shell_range64
    pop r14
    pop r12
    ret
x86_64_elf64_address_flags64:
    ; The globally selected shell has only page0; the child also owns R page1.
    cmp rax, 0x401000
    jae .absent
    mov eax, 5
    ret
.absent:
    xor eax, eax
    ret
'''+body
        c='''#include <stdint.h>
#include <stdio.h>
extern int __attribute__((sysv_abi)) legacy_access(uint64_t);
int main(void) {
    if(legacy_access(0x400100)!=1 || legacy_access(0x401100)!=0)return 1;
    puts("USER_ACCESS_LEGACY_OK child_R_page_rejected_by_parent_image=1");return 0;
}
'''
        host_builder.TaskFrameTests().build(asm,c,'USER_ACCESS_LEGACY')

    def test_actual_core(self):
        host_builder.TaskFrameTests().build(ROOT/'arch/x86_64/mm/user_access.asm',
            ROOT/'test/x86_64_user_access_host.c','USER_ACCESS_HOST')

    def test_runtime_oracle(self):
        from run_qemu_x86_64_user_access import validate
        serial=''.join(f'REIST_X86_64_CHILD_EXIT_REAP_OK status=0000004D generation={g:02X} parent=07 queued=00 rip=0000000000400444\nREIST_X86_64_RING3_SHELL_RUN_OK\nMAPPING_OK\n' for g in (41,42))
        validate(serial,0x400444)
        for bad in (serial+serial,serial.replace('MAPPING_OK','',1),serial.replace('0000004D','0000004E',1),
                    serial.replace('generation=2A','generation=29'),serial.replace('queued=00','queued=01',1),
                    serial.replace('400444','400445',1)):
            with self.assertRaises(RuntimeError):validate(bad,0x400444)

if __name__=='__main__':unittest.main()
