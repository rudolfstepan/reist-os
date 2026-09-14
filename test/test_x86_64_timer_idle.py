"""Execute production native IRQ transaction and CPL0 idle admission at O0/O2.

CR3/RDTSC/OUT are the only privileged instruction adapters. Whole-run ownership
is an explicit precondition fixture; its separate production host group remains
required. No claim to execute unrelated CPL3 or legacy timer branches here.
"""
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'test'))
import test_x86_64_task_frames as builder


def function(source,name):
    match=re.search(r'^'+name+r':\n.*?(?=^[A-Za-z_]\w*:|\Z)',source,re.M|re.S)
    if not match:raise ValueError('missing production function '+name)
    return match.group()


def assembly():
    timer=(ROOT/'arch/x86_64/cpu/timer_interrupt.asm').read_text()
    process=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
    scheduler=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
    irq=timer.split('\n.runtime:\n',1)[1].split('\n.invalid:\n',1)[0]
    if irq.count('    rdtsc\n')!=1:raise ValueError('RDTSC adapter extent')
    irq=irq.replace('    rdtsc\n','    mov eax,[rel host_now]\n    mov edx,[rel host_now+4]\n')
    if irq.count('    out PIC1_COMMAND,al')!=1 or irq.count('    out PIC1_COMMAND, al')!=1 or irq.count('    out PIC1_DATA, al')!=1:
        raise ValueError('PIO adapter extent')
    for old,new in (('out PIC1_COMMAND,al','call host_eoi'),('out PIC1_COMMAND, al','call host_eoi'),('out PIC1_DATA, al','call host_mask')):
        irq=irq.replace(old,new)
    # The selected runtime block closes its source-level native conditional.
    irq='%ifdef REIST_NATIVE_RUNTIME\n'+irq
    idle=function(process,'process_run_irq_validate64').split('\n.idle:\n',1)[1]
    if idle.count('    mov rax, cr3\n')!=1:raise ValueError('CR3 adapter extent')
    idle=idle.replace('    mov rax, cr3\n','    mov rax,[rel host_cr3]\n')
    returned=function(process,'process_run_irq_tail64').rsplit('\n.idle:\n',1)[1]
    # The extracted idle arm starts inside the enclosing heap conditional.
    constants=[]
    for line in scheduler.splitlines():
        if re.match(r'^(EXCEPTION_FRAME_\w+|KERNEL_CODE_SELECTOR|KERNEL_DATA_SELECTOR)\s+equ\s+',line):constants.append(line)
    for name in ('TIMER_VECTOR','TSC_DEADLINE_CYCLES','PIC_EOI','PIC_ALL_MASKED'):
        match=re.search(r'^'+name+r'\s+equ\s+[^\n]+',timer,re.M)
        if not match:raise ValueError('constant '+name)
        constants.append(match.group())
    labels=['host_now','host_cr3','host_ownership','host_context_calls','host_tick_calls',
            'host_abort_calls','host_eoi_calls','host_mask_calls','host_tail_calls',
            'host_eoi_tick','host_eoi_deadline','host_tail_tick','host_reason','host_sequence',
            'host_context_seq','host_tick_seq','host_eoi_seq','host_tail_seq',
            'timer_generation','timer_deadline','timer_runtime_ticks','timer_runtime_eois',
            'scheduler_last_tick','scheduler_original_cr3','scheduler_runqueue_count',
            'scheduler_deadline_count','process_run_live','process_heap_retire_mask','process_heap_pending_mask']
    return '''BITS 64
%define REIST_NATIVE_RUNTIME 1
%define REIST_NATIVE_HEAP_BINDING 1
'''+ '\n'.join(constants)+'''
section .bss
alignb 16
global host_state
host_state:
'''+ '\n'.join(name+': resq 1' for name in labels)+'''
global scheduler_kernel_stack_bottom,scheduler_kernel_stack_top
alignb 16
scheduler_kernel_stack_bottom: resb 16384
scheduler_kernel_stack_top:
section .text
global host_idle_wait,host_idle_resume,host_work_wait,host_work_resume
process_run_dispatch64:
.idle_wait:
host_idle_wait: times 3 nop
process_run_dispatch64.idle_resume:
host_idle_resume: nop
times 16 nop
process_run_dispatch64.work_wait:
host_work_wait: times 3 nop
process_run_dispatch64.work_resume:
host_work_resume: nop
global timer_irq_host
timer_irq_host:
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
    call native_irq
    mov [rel host_reason],r9
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
    ret
native_irq:
    xor r9d,r9d
'''+irq+'''
global idle_host
idle_host:
    cmp qword [rel host_ownership],1
    jne .bad
    cmp qword [rdi+EXCEPTION_FRAME_CS],KERNEL_CODE_SELECTOR
    jne .bad
'''+idle+'''
x86_64_scheduler_shell_timer_validate64:
    inc qword [rel host_context_calls]
    push rax
    inc qword [rel host_sequence]
    mov rax,[rel host_sequence]
    mov [rel host_context_seq],rax
    pop rax
    jmp idle_host
x86_64_scheduler_deadline_tick64:
    inc qword [rel host_tick_calls]
    push rax
    inc qword [rel host_sequence]
    mov rax,[rel host_sequence]
    mov [rel host_tick_seq],rax
    pop rax
    jmp process_run_tick_admit64
x86_64_scheduler_timer_abort64:
    inc qword [rel host_abort_calls]
    xor eax,eax
    ret
x86_64_scheduler_shell_timer_tail64:
    inc qword [rel host_tail_calls]
    mov [rel host_tail_tick],rsi
    inc qword [rel host_sequence]
    mov rax,[rel host_sequence]
    mov [rel host_tail_seq],rax
    jmp idle_return_host
global idle_return_host
idle_return_host:
'''+returned+'''
host_mask:
    pushfq
    inc qword [rel host_mask_calls]
    popfq
    ret
host_eoi:
    pushfq
    push rax
    inc qword [rel host_eoi_calls]
    inc qword [rel host_sequence]
    mov rax,[rel host_sequence]
    mov [rel host_eoi_seq],rax
    mov rax,[rel timer_runtime_ticks]
    mov [rel host_eoi_tick],rax
    mov rax,[rel timer_deadline]
    mov [rel host_eoi_deadline],rax
    pop rax
    popfq
    ret
'''+function(timer,'timer_runtime_progress64')+function(process,'process_run_tick_admit64')


class TimerIdleTests(unittest.TestCase):
    def test_actual_native_irq_idle_transaction(self):
        builder.TaskFrameTests().build(assembly(),ROOT/'test/x86_64_timer_idle_host.c','TIMER_IDLE_HOST')


if __name__=='__main__':unittest.main()
