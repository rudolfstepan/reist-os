"""Actual bounded capture assembly and the exact debugger-side consumer."""
from pathlib import Path
import re,struct,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
from test_x86_64_program_memory import build_actual
import run_qemu_x86_64_block_profile as profile


class PioTraceTests(unittest.TestCase):
    def test_actual_capture_and_cleanup(self):
        source=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text()
        code=source.split('; BEGIN_PIO_TRACE',1)[1].split('; END_PIO_TRACE',1)[0]
        asm='BITS 64\nNATIVE_TASK_SHIFT equ 10\nsection .text\n'+code
        asm+='\nglobal native_pio_trace_out64,native_pio_trace_data64,native_pio_trace_clear64\n'
        asm+=(ROOT/'test/x86_64_pio_trace_host.c').read_text().split('/* ASM\n',1)[1].split('\nASM */',1)[0]
        asm+='\nsection .bss\nalign 16\nglobal trace_guard_before,native_pio_trace,trace_guard_after,native_pio_state,native_pio_request,scheduler_tasks,scheduler_current_slot,family_records,capture_registers,capture_after,trace_data\n'
        asm+='trace_guard_before: resq 2\nnative_pio_trace: resb 12304\ntrace_guard_after: resq 2\nnative_pio_state: resb 64\nnative_pio_request: resb 64\nscheduler_tasks: resb 4096\nscheduler_current_slot: resq 1\nalignb 16\nfamily_records: resb 256\ncapture_registers: resq 17\nalignb 16\ncapture_after: resq 17\nalignb 16\ntrace_data: resb 64\n'
        build_actual(asm,(ROOT/'test/x86_64_pio_trace_host.c').read_text(),'pio_trace')

    def test_physical_order_and_profile_only(self):
        source=(ROOT/'arch/x86_64/devices/pio_domain.inc').read_text()
        out=source.split('native_pio_out8:',1)[1].split('native_pio_syscall64:',1)[0]
        self.assertRegex(out,r'out dx,al\s+\.done:\s+%ifdef REIST_NATIVE_PIO_TRACE\s+call native_pio_trace_out64')
        transfer=source.split('.word:',1)[1].split('.bind:',1)[0]
        self.assertLess(transfer.index('mov [rdx+rbp*2],ax'),transfer.index('call native_pio_trace_data64'))
        self.assertIn('%ifdef REIST_NATIVE_PIO_TRACE\n; BEGIN_PIO_TRACE',source)
        self.assertIn('%ifdef REIST_NATIVE_PIO_TRACE\nnative_pio_trace: resb 12304',source)
        make=(ROOT/'Makefile').read_text()
        self.assertEqual(make.count('-DREIST_NATIVE_PIO_TRACE=1'),1)
        self.assertIn('$(if $(filter 1,$(X86_64_NATIVE_BLOCK_PROFILE)),-DREIST_NATIVE_PIO_TRACE=1,)',make)

    def test_consumer_metadata_mutations(self):
        state=(3<<32|2,~(3<<32|2)&((1<<64)-1),0,1,2,3,1,0)
        raw=bytearray(12304);struct.pack_into('<Q',raw,0,1)
        struct.pack_into('<2Q8Q5Q',raw,16,1,1,*state,0x3f6,6,0,1,1<<32)
        decoded=profile.trace_decode(bytes(raw),0)
        self.assertEqual(len(decoded),1);self.assertEqual(decoded[0][:2],(1,1))
        for offset,value in ((0,4097),(8,1),(16,3),(24,0),(24,2),(16+120,1),(16+16+8,0),(16+16+56,1),(16+16+40,65),(16+96,4),(16+112,7)):
            bad=bytearray(raw);struct.pack_into('<Q',bad,offset,value)
            with self.assertRaises(ValueError):profile.trace_decode(bytes(bad),0)
        for last in (-1,2,4097):
            with self.assertRaises(ValueError):profile.trace_decode(bytes(raw),last)
        for size in (0,12303,12305):
            with self.assertRaises(ValueError):profile.trace_decode(bytes(size),0)
        bad=bytearray(raw);struct.pack_into('<Q',bad,0,65)
        with self.assertRaisesRegex(ValueError,'trace gap'):profile.trace_decode(bytes(bad),0)
        self.assertEqual(profile.trace_decode(bytes(raw),1),[])
        profile.trace_clean(bytes(12304))
        for n in range(12304):
            bad=bytearray(12304);bad[n]=1
            with self.assertRaisesRegex(ValueError,'trace cleanup'):profile.trace_clean(bytes(bad))

    def test_exact_data_oracle_and_ring_sequence(self):
        owner=3<<32|2;state=(owner,owner^0xffffffffffffffff,0,1,2,3,1,0)
        # Actual shared out/data callbacks, without debugger memory or registers.
        ns={'struct':struct,'devices':{},'pio_owner':0,'port_events':0,'emit':lambda *a,**k:None}
        exec('def out(event):'+profile.EXTRA.split('def out(event):',1)[1].split('def pio_retire',1)[0],ns)
        ns['out']((1,1,state,(0x3f6,6,0,1,1<<32),b'',0))
        ns['out']((1,2,(owner,state[1],0,1,2,3,1,0),(0x3f6,2,2,3,1<<32),b'',0))
        item=ns['devices'][owner];item['command']=0x20;item['lba']=0
        raw=bytearray(12304);struct.pack_into('<Q',raw,0,1)
        struct.pack_into('<2Q8Q',raw,16,2,1,*state)
        struct.pack_into('<4IQ4I3Q',raw,96,2,64,4,0,owner,0x1f0,0,16,0,0x408000,100,0)
        raw[160:192]=bytes(n^0xa5 for n in range(32));struct.pack_into('<Q',raw,192,16)
        event=profile.trace_decode(bytes(raw),0)[0];ns['data'](event)
        self.assertEqual(item['data'],raw[160:192])
        for n in range(32):
            bad=bytearray(raw);bad[160+n]^=1;item['data'].clear()
            with self.assertRaisesRegex(ValueError,'trace data'):ns['data'](profile.trace_decode(bytes(bad),0)[0])
        for offset,value in ((96,3),(100,63),(104,3),(108,1),(112,owner+1),(120,0x1f1),(124,1),(128,0),(128,17),(132,1),(136,0),(136,0x408001),(144,20),(144,1021),(152,1),(192,0),(192,17),(200,1)):
            bad=bytearray(raw);struct.pack_into('<Q' if offset>=136 or offset==112 else '<I',bad,offset,value)
            with self.assertRaises(ValueError):profile.trace_decode(bytes(bad),0)
        for words in range(1,17):
            v=bytearray(raw);struct.pack_into('<I',v,128,words);struct.pack_into('<Q',v,192,words);v[160+2*words:192]=bytes(32-2*words)
            self.assertEqual(profile.trace_decode(bytes(v),0)[0][5],words)
            if words<16:
                v[160+2*words]=1
                with self.assertRaises(ValueError):profile.trace_decode(bytes(v),0)
        record=bytes(raw[16:208]);ring=bytearray(12304)
        for end in (64,65,4096):
            struct.pack_into('<Q',ring,0,end)
            for seq in range(end-63,end+1):
                start=16+((seq-1)&63)*192;ring[start:start+192]=record;struct.pack_into('<Q',ring,start+8,seq)
            self.assertEqual([e[1] for e in profile.trace_decode(bytes(ring),end-64)],list(range(end-63,end+1)))
            for last in (end,end-1,end-32,end-64):
                reads=[]
                def read(address,size):
                    self.assertTrue(0<=address<12304 and 0<size<=12304-address);reads.append((address,size))
                    return ring[address:address+size]
                self.assertEqual(profile.trace_decode(profile.trace_snapshot(read,0,last),last),profile.trace_decode(bytes(ring),last))
                self.assertLessEqual(len(reads),3)
                self.assertEqual(sum(size for _,size in reads),16+(end-last)*192)
            for slot in range(64):
                bad=bytearray(ring);start=16+slot*192;bad[start:start+192]=bytes(192)
                with self.assertRaises(ValueError):profile.trace_decode(bytes(bad),end-64)
                bad=bytearray(ring);other=16+((slot+1)&63)*192;bad[start:start+192]=bad[other:other+192]
                with self.assertRaises(ValueError):profile.trace_decode(bytes(bad),end-64)

    def test_paused_user_snapshot_equivalence(self):
        memory={};reads=[];data=bytes(n&255 for n in range(4096))*67
        # Four-level mappings across a PDE boundary, including noncontiguous
        # data pages. The new batching must return exactly the previous walker.
        dm=0xffff800000000000;mask=0x3fffff000
        for address,value in ((0x1000,0x2001),(0x2000,0x3001),(0x3008,0x4001),(0x3010,0x5001)):
            memory[dm+address]=value
        for n in range(67):
            va=0x3f0000+n*4096;pt=0x4000 if va<0x400000 else 0x5000
            frame=0x100000000+n*8192
            memory[dm+pt+((va>>12)&511)*8]=frame|7
        def q(a):reads.append(a);return memory.get(a,0)
        def mem(a,n):
            self.assertLessEqual(n,4096)
            return data[(a-dm-0x100000000)//8192*4096+(a&4095):(a-dm-0x100000000)//8192*4096+(a&4095)+n]
        ns={'q':q,'mem':mem,'DM':dm,'MASK':mask}
        exec('def user(t,va,n):'+profile.EXTRA.split('def user(t,va,n):',1)[1].split('def trace_expected_rejection',1)[0],ns)
        t=(0,0,0x1000)
        self.assertEqual(ns['user'](t,0x3f0003,266336),data[3:266339])
        self.assertEqual(len(reads),70);self.assertEqual(len(reads),len(set(reads)))
        memory[dm+0x5000]=0
        with self.assertRaises(AssertionError):ns['user'](t,0x400000,1)


if __name__=='__main__':unittest.main()
