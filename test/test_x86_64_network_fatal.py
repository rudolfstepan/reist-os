"""Actual emergency assembly with only privileged IO replaced by register mocks."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid,json,hashlib,shutil,struct
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig

class NetworkFatal(unittest.TestCase):
    def test_actual_repeated_terminal_snapshot(self):
        import run_qemu_x86_64_network_fatal as guest
        base=ROOT/'build/codex-agent/r83bk-network-fatal';source=base/'candidate02/guests/child-crash'
        c=json.loads((source/'config.json').read_text());s=c['s'];cs=c['cs']
        events=[json.loads(l[8:]) for l in (source/'frame-trace.log').read_text().splitlines() if l.startswith('NETWORK ')]
        events=[e for e in events if e['kind']=='terminal'][:2]
        addresses={'state':cs['native_network_state'],'dma':cs['native_network_dma'],'staging':s['native_network_call'],
            'tasks':s['scheduler_tasks'],'profiles':s['family_profiles'],'family':s['family_records'],
            'cpu':s['scheduler_cpu_budgets'],'receipt':s['process_run_receipt']}
        for altered in (False,True):
            folder=base/('repeat-host-'+uuid.uuid4().hex);folder.mkdir();current=[0];seen=[]
            def mem(address,size):
                k=next(k for k,a in addresses.items() if a==address);raw=(source/events[current[0]]['raw'][k]['file']).read_bytes()
                self.assertEqual(len(raw),size)
                if altered and current[0] and k=='state':raw=bytes([raw[0]^1])+raw[1:]
                return raw
            def d(address):return 1 if address==s['scheduler_current_slot'] else events[current[0]]['initial']
            def q(address):return events[current[0]]['ticks' if address==s['timer_runtime_ticks'] else 'eois']
            def snapshot(kind,slot):seen.append((kind,slot));scope['sequence']+=1
            scope=dict(S=s,CS=cs,CONFIG=c,F=folder,struct=struct,json=json,hashlib=hashlib,mode=lambda:8,mem=mem,d=d,q=q,
                free=lambda:events[current[0]]['free'],snapshot=snapshot,sequence=0)
            exec(guest.REPEAT_TERMINAL,scope);scope['terminal']();current[0]=1
            if altered:
                with self.assertRaisesRegex(AssertionError,'changed repeated terminal'):scope['terminal']()
                self.assertFalse((folder/'repeated-stops.jsonl').exists())
            else:
                scope['terminal']();self.assertEqual(len((folder/'repeated-stops.jsonl').read_text().splitlines()),1)
            self.assertEqual(seen,[('terminal',1)])
    def test_corruption_at_validation_boundary(self):
        import run_qemu_x86_64_network_fatal as guest
        base=ROOT/'build/codex-agent/r83bk-network-fatal';source=base/'diagnostic02';image=base/'build01/x86_64/reist-x86_64-bootstrap.elf'
        self.assertTrue(guest.review(image,source,'corrupt-io')['preserved'])
        for field,offset,value in (('call',8,5),('damaged',64,0xc100)):
            folder=base/('corruption-mutation-'+uuid.uuid4().hex);shutil.copytree(source,folder)
            c=json.loads((folder/'config.json').read_text());c['folder']=folder.as_posix();(folder/'config.json').write_text(json.dumps(c),encoding='utf-8')
            lines=(folder/'frame-trace.log').read_text().splitlines()
            for i,line in enumerate(lines):
                if not line.startswith('NETFATAL '):continue
                e=json.loads(line[9:])
                if e['kind']!='inject':continue
                item=e[field];p=folder/item['file'];raw=bytearray(p.read_bytes());struct.pack_into('<Q',raw,offset,value);p.write_bytes(raw)
                item['sha256']=hashlib.sha256(raw).hexdigest();lines[i]='NETFATAL '+json.dumps(e);break
            (folder/'frame-trace.log').write_text('\n'.join(lines)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError,msg=field):guest.review(image,folder,'corrupt-io')
    def test_real_fatal_replay_rejects_mutations(self):
        import run_qemu_x86_64_network_fatal as guest
        base=ROOT/'build/codex-agent/r83bk-network-fatal';source=base/'diagnostic01';image=base/'build01/x86_64/reist-x86_64-bootstrap.elf'
        self.assertTrue(guest.review(image,source,'kernel-nx')['probe'])
        for event,field,offset,value in (('fence','receipt',32,5),('halt','preserved',384,1),('exception','frame',18*8,0x33)):
            folder=base/('mutation-'+uuid.uuid4().hex);shutil.copytree(source,folder)
            c=json.loads((folder/'config.json').read_text());c['folder']=folder.as_posix();(folder/'config.json').write_text(json.dumps(c),encoding='utf-8')
            lines=(folder/'frame-trace.log').read_text().splitlines()
            for i,line in enumerate(lines):
                if not line.startswith('NETFATAL '):continue
                e=json.loads(line[9:])
                if e['kind']!=event:continue
                item=e[field];p=folder/item['file'];raw=bytearray(p.read_bytes());struct.pack_into('<Q',raw,offset,value);p.write_bytes(raw)
                item['sha256']=hashlib.sha256(raw).hexdigest();lines[i]='NETFATAL '+json.dumps(e);break
            (folder/'frame-trace.log').write_text('\n'.join(lines)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError,msg=field):guest.review(image,folder,'kernel-nx')
    def test_shared_fatal_path(self):
        source=(ROOT/'arch/x86_64/cpu/exceptions.asm').read_text(encoding='utf-8')
        self.assertIn('%ifdef REIST_NATIVE_NETWORK_DMA\n    call native_network_emergency64\n%endif',source)
        source=(ROOT/'arch/x86_64/devices/network_domain.inc').read_text(encoding='utf-8')
        body=source.split('native_network_emergency64:\n',1)[1].split('section .bss',1)[0]
        self.assertNotIn('call ',body);self.assertNotIn('native_network_call',body)
        self.assertIn('cli\n',body);self.assertIn('native_network_fatal_receipt',body)
        self.assertIn('$(X86_64_NETWORK_FLAGS) arch/x86_64/cpu/exceptions.asm',(ROOT/'Makefile').read_text(encoding='utf-8'))
    def test_actual_assembly(self):
        source=(ROOT/'arch/x86_64/devices/network_domain.inc').read_text(encoding='utf-8')
        body='native_network_emergency64:\n'+source.split('native_network_emergency64:\n',1)[1].split('section .bss',1)[0]
        self.assertNotIn('call ',body)
        out=ROOT/'build/codex-agent/r83bk-network-fatal'/('host-'+uuid.uuid4().hex);out.mkdir(parents=True)
        (out/'mock.asm').write_text(MOCK_PREFIX+body+MOCK_IO,encoding='ascii')
        (out/'host.c').write_text(HOST,encoding='ascii')
        env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(ROOT/'build/zig-global-cache'),ZIG_LOCAL_CACHE_DIR=str(out/'cache'))
        r=subprocess.run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',str(out/'mock.asm'),'-o',str(out/'mock.obj')],cwd=ROOT,capture_output=True,timeout=30)
        self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'))
        for opt in ('-O0','-O2'):
            exe=out/(opt+'.exe')
            r=subprocess.run([str(find_zig()),'cc','-target','x86_64-windows-gnu',opt,'-Wno-unused-command-line-argument','-fno-sanitize=all','-Wall','-Wextra','-Werror',str(out/'host.c'),str(out/'mock.obj'),'-o',str(exe)],cwd=ROOT,env=env,capture_output=True,timeout=120)
            self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'))
            r=subprocess.run([exe],capture_output=True,timeout=5);self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'))
            self.assertIn(b'NETWORK_FATAL_ASM_OK',r.stdout)

MOCK_PREFIX='''BITS 64
global native_network_emergency64,native_network_fatal_receipt,hw
%macro cli 0
%endmacro
%macro in 2
    call test_in
%endmacro
%macro out 2
    call test_out
%endmacro
section .text
'''
MOCK_IO='''
test_in:
    pushfq
    inc dword [rel hw+28]
    cmp dx,0xcfc
    je .pci
    cmp dx,0xc037
    je .command
    cmp dx,0xc03c
    je .imr
    inc dword [rel hw+36]
    xor eax,eax
    jmp .end
.command: mov eax,[rel hw+16]
    jmp .end
.imr: mov eax,[rel hw+12]
    jmp .end
.pci:
    mov eax,[rel hw+24]
    cmp eax,0x80002000
    je .id
    cmp eax,0x80002010
    je .bar
    cmp eax,0x80002004
    je .config
    inc dword [rel hw+36]
    xor eax,eax
    jmp .end
.id: mov eax,[rel hw]
    jmp .end
.bar: mov eax,[rel hw+4]
    jmp .end
.config: mov eax,[rel hw+8]
.end: popfq
    ret
test_out:
    pushfq
    inc dword [rel hw+32]
    cmp dx,0xcf8
    je .address
    cmp dx,0xcfc
    je .config
    cmp dx,0xc037
    je .command
    cmp dx,0xc03c
    je .imr
    inc dword [rel hw+36]
    jmp .end
.address: mov [rel hw+24],eax
    jmp .end
.config:
    cmp dword [rel hw+24],0x80002004
    jne .bad
    mov [rel hw+8],ax
    test dword [rel hw+20],1
    jz .end
    or dword [rel hw+8],4
    jmp .end
.command:
    test dword [rel hw+20],2
    jnz .end
    mov [rel hw+16],al
    jmp .end
.imr:
    test dword [rel hw+20],4
    jnz .end
    mov [rel hw+12],ax
    jmp .end
.bad: inc dword [rel hw+36]
.end: popfq
    ret
section .bss
alignb 8
native_network_fatal_receipt: resq 8
hw: resd 10
'''
HOST=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern void native_network_emergency64(void);
extern uint64_t native_network_fatal_receipt[8];
extern uint32_t hw[10];
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line %u: %s\n",__LINE__,#x);abort();}}while(0)
static void reset(void){uint32_t init[10]={0x813910ec,0xc001,5,0xffff,12,0,0,0,0,0};memcpy(hw,init,sizeof(init));memset(native_network_fatal_receipt,0xa5,64);}
static void run(unsigned status){native_network_emergency64();CHECK(native_network_fatal_receipt[0]==0x3145434e45464e52ULL);CHECK(native_network_fatal_receipt[7]==status);CHECK(!hw[9] && hw[7]<=6 && hw[8]<=6);}
int main(void){
    reset();run(1);CHECK(hw[2]==1 && !hw[3] && !hw[4]);CHECK(native_network_fatal_receipt[3]==5 && native_network_fatal_receipt[4]==1);hw[7]=hw[8]=0;run(1);
    for(unsigned bit=1;bit<=4;bit*=2){reset();hw[5]=bit;run(4);}
    reset();hw[0]=0xffffffff;run(2);CHECK(hw[2]==5 && hw[3]==0xffff && hw[4]==12);
    reset();hw[0]=0;run(2);CHECK(hw[2]==5);
    reset();hw[0]=0x12345678;run(3);CHECK(hw[2]==5);
    const uint32_t bad[]={0xc000,0xc005,0x10001,0xffc001,0x101};
    for(unsigned n=0;n<sizeof(bad)/sizeof(bad[0]);n++){reset();hw[1]=bad[n];run(3);CHECK(hw[2]==1 && hw[3]==0xffff && hw[4]==12);}
    puts("NETWORK_FATAL_ASM_OK");return 0;
}
'''
if __name__=='__main__':unittest.main()
