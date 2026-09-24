"""Execute the exact fixed-capacity C transport included in the QEMU patch."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys
import json
import os
import socket
import struct
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def transport_header():
    patch = (ROOT / "scripts/qemu_x86_64_large_file_observer.patch").read_text()
    section = patch.split("+++ b/gdbstub/reist-observer.h\n")
    if len(section) != 2:
        raise ValueError("missing/duplicate transport implementation")
    lines = section[1].splitlines()
    if not lines[0].startswith("@@ ") or any(
        not line.startswith("+") for line in lines[1:]
    ):
        raise ValueError("unexpected new-header patch")
    return "\n".join(line[1:] for line in lines[1:]) + "\n"


HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include "reist-observer.h"
static unsigned calls, fail_at;
static int read_ram(void *opaque, uint64_t address, unsigned char *p, size_t n)
{
    size_t i;
    (void)opaque;
    ++calls;
    if (calls == fail_at) { return 0; }
    for (i = 0; i < n; ++i) { p[i] = (unsigned char)(address + i); }
    return 1;
}
static void reject(const char *request, int expected, unsigned reads)
{
    unsigned char output[BV_REPLY], before[BV_REPLY];
    uint64_t seq = 0;
    size_t n = sizeof(output);
    memset(output, 0xa5, sizeof(output));
    memcpy(before, output, sizeof(output));
    calls = 0;
    assert(bv_query(request, &seq, read_ram, NULL, output, &n) == expected);
    assert(!seq && n == sizeof(output) && calls == reads);
    assert(!memcmp(output, before, sizeof(output)));
}
int main(void)
{
    const char *invalid[] = {
        "", "1", "2;1;1;ffffffff80100000,1",
        "01;1;1;ffffffff80100000,1", "1;0;1;ffffffff80100000,1",
        "1;2;1;ffffffff80100000,1", "1;40001;1;ffffffff80100000,1",
        "1;1;0;", "1;1;21;ffffffff80100000,1",
        "1;1;1;ffffffff80100000,0", "1;1;1;ffffffff80100000,601",
        "1;1;1;ffffffff80100000,01", "1;1;1;FFFFFFFF80100000,1",
        "1;1;1;ffffffff80100000,1;", "1;1;1;ffffffff80100000,1junk",
        "1;1;1;1ffffffff80100000,1", "1;1;1;0,1",
        "1;1;1;ffffffff800fffff,1", "1;1;1;ffffffff87ffffff,2",
        "1;1;1;ffffffff88000000,1", "1;1;1;ffffffffffffffff,2",
        "1;1;1;ffff8000ffffffff,1", "1;1;1;ffff800400000000,1",
        "1;1;1;ffff8003ffffffff,2",
        "1;1;2;ffffffff80100000,8;ffffffff80100007,1",
        "1;1;2;ffffffff80100000,8;ffffffff80100000,8",
        "1;1;2;ffffffff80100000,8;ffff800100000000,8",
        "1;1;2;ffffffff80100000,1;ffffffff80100008,600",
        "1;1;2;ffffffff80100000,1"
    };
    unsigned char output[BV_REPLY], expected[BV_REPLY];
    uint64_t seq = 0;
    size_t n = sizeof(output), i;
    const char *valid = "1;1;2;ffff800100000001,3;ffffffff80100002,2";
    for (i = 0; i < sizeof(invalid)/sizeof(invalid[0]); ++i) {
        reject(invalid[i], -1, 0);
    }
    fail_at = 2;
    reject(valid, -2, 2);
    fail_at = 0; calls = 0;
    memset(expected, 0, sizeof(expected));
    /* Independently constructed wire bytes; descriptors interleave payloads. */
    memcpy(expected, "RBV1\1\0\0\0\0\0\0\0\2\0\5\0", 16);
    memcpy(expected+16, "\1\0\0\0\1\200\377\377\3\0\0\0\1\2\3", 15);
    memcpy(expected+31, "\2\0\20\200\377\377\377\377\2\0\0\0\2\3", 14);
    assert(bv_query(valid, &seq, read_ram, NULL, output, &n) == 0);
    assert(seq == 1 && calls == 2 && n == 45 && !memcmp(output, expected, n));
    calls = 0; n = sizeof(output);
    assert(bv_query(valid, &seq, read_ram, NULL, output, &n) == -1);
    assert(!calls && seq == 1);
    seq = 0; n = 44;
    assert(bv_query(valid, &seq, read_ram, NULL, output, &n) == -1);
    assert(!calls && !seq && n == 44);
    seq = 262143; n = sizeof(output);
    assert(!bv_query("1;40000;1;ffffffff80100000,1", &seq,
                     read_ram, NULL, output, &n));
    assert(seq == 262144);
    calls = 0;
    assert(bv_query("1;40001;1;ffffffff80100000,1", &seq,
                    read_ram, NULL, output, &n) == -1 && !calls);
    {
        char request[2048];
        size_t used = (size_t)sprintf(request, "1;1;20;");
        for (i = 0; i < 32; ++i) {
            used += (size_t)sprintf(request + used, "%llx,30%s",
                (unsigned long long)(UINT64_C(0xffffffff80100000)+i*48),
                i == 31 ? "" : ";");
        }
        seq = 0; n = sizeof(output); calls = 0;
        assert(!bv_query(request, &seq, read_ram, NULL, output, &n));
        assert(seq == 1 && calls == 32 && n == BV_REPLY);
    }
    puts("BV bounded RAM transport OK");
    return 0;
}
'''


CONTROL_HARNESS = r'''
typedef struct {
    BvControl *control;
    uint64_t now;
    unsigned fail, call, records, arms, drops, resumes, owned;
} Platform;
static uint64_t host_clock(void *p) { return ((Platform *)p)->now; }
static int step(Platform *p) { return ++p->call != p->fail; }
static int save_record(void *opaque, unsigned after, uint64_t seq,
                       const BvStop *stop)
{
    Platform *p = opaque;
    assert(seq && stop->cpu.rip);
    assert(p->control->state == (after ? BV_CTL_AFTER : BV_CTL_RECORD));
    ++p->records;
    return step(p);
}
static int arm_target(void *opaque, uint64_t target, uint64_t physical)
{
    Platform *p = opaque;
    assert(target && physical && !p->owned);
    assert(p->control->state == BV_CTL_INSTALL);
    ++p->arms;
    if (!step(p)) { return 0; }
    p->owned = 1;
    return 1;
}
static int drop_target(void *opaque, uint64_t target, uint64_t physical)
{
    Platform *p = opaque;
    assert(target && physical && p->owned);
    ++p->drops;
    if (!step(p)) { return 0; }
    p->owned = 0;
    return 1;
}
static int resume_vm(void *opaque)
{
    Platform *p = opaque;
    assert(p->control->state == BV_CTL_WAIT ||
           p->control->state == BV_CTL_ARMED);
    ++p->resumes;
    return step(p);
}
static void setup(BvControl *c, Platform *p, BvControlOps *ops, BvStop *s)
{
    uint64_t sites[3] = {0xffffffff80110000ULL,0xffffffff80110001ULL,
                         0xffffffff80110002ULL};
    uint64_t targets[3] = {0xffffffff8010eae5ULL,0xffffffff8010eca5ULL,
                           0xffffffff8010ecb3ULL};
    unsigned i;
    memset(c,0,sizeof(*c)); memset(p,0,sizeof(*p)); memset(s,0,sizeof(*s));
    p->control=c; p->now=100;
    *ops=(BvControlOps){host_clock,save_record,arm_target,drop_target,resume_vm};
    assert(bv_control_arm(c,sites,targets,1,300100,ops,p));
    s->cpu.rip=sites[0]; s->cpu.rsp=0xffffffff80130000ULL;
    for(i=0;i<17;i++){s->cpu.reg[i]=i+1;}
    s->cpu.reg[15]=2; /* RFLAGS: IF must be clear at the cold RET. */
    s->target=targets[0]; s->binding[0]=0x110000;
    s->binding[1]=0x10eae5; s->binding[2]=0x130000;
    s->actual_breakpoint=1; s->ret_opcode=0xc3;
}
static BvStop returned(BvStop s)
{
    s.cpu.rip=s.target; s.cpu.rsp+=8;
    return s;
}
static void control_tests(void)
{
    BvControl c; Platform p; BvControlOps ops; BvStop s,t;
    unsigned i,j;
    setup(&c,&p,&ops,&s);
    t=s; t.cpu.rip++;
    /* Another configured site with the wrong target must fail, not hand off. */
    assert(bv_control_stop(&c,&t,&ops,&p)==-1);
    assert(!p.call && c.state==BV_CTL_FAILED);
    for(i=0;i<3;i++) {
        setup(&c,&p,&ops,&s);
        s.cpu.rip=c.sites[i];s.target=c.targets[i];
        s.binding[0]=s.cpu.rip-0xffffffff80000000ULL;
        s.binding[1]=s.target-0xffffffff80000000ULL;
        assert(bv_control_stop(&c,&s,&ops,&p)==1);
        assert(c.state==BV_CTL_WAIT && p.owned && c.events==0);
        t=returned(s);
        assert(bv_control_stop(&c,&t,&ops,&p)==1);
        assert(c.state==BV_CTL_ARMED && !p.owned && c.events==1);
        assert(p.records==2 && p.arms==1 && p.drops==1 && p.resumes==2);
    }
    /* Every platform operation can fail; nothing resumes after the failure. */
    for(i=1;i<=6;i++) {
        unsigned resumes;
        setup(&c,&p,&ops,&s); p.fail=i;
        j=(unsigned)bv_control_stop(&c,&s,&ops,&p);
        if(j==1){t=returned(s);assert(bv_control_stop(&c,&t,&ops,&p)==-1);}
        else {assert(j==(unsigned)-1);}
        assert(c.state==BV_CTL_FAILED && p.owned==(i==5));
        resumes=p.resumes;
        assert(bv_control_stop(&c,&s,&ops,&p)==-1 && resumes==p.resumes);
        assert(!bv_control_arm(&c,c.sites,c.targets,1,200,&ops,&p));
    }
    /* Mutate each actual after-register and each physical binding independently. */
    for(i=0;i<23;i++){
        setup(&c,&p,&ops,&s);
        assert(bv_control_stop(&c,&s,&ops,&p)==1);t=returned(s);
        if(i<17){t.cpu.reg[i]^=1;}
        else if(i==17){t.cpu.rip++;}
        else if(i==18){t.cpu.rsp++;}
        else if(i<22){t.binding[i-19]++;}
        else {t.actual_breakpoint=0;}
        assert(bv_control_stop(&c,&t,&ops,&p)==-1);
        assert(!p.owned && p.records==1 && p.resumes==1);
    }
    for(i=0;i<7;i++){
        setup(&c,&p,&ops,&s);
        if(i==0){s.ret_opcode=0x90;}
        if(i==1){s.actual_breakpoint=0;}
        if(i==2){s.cpu.reg[15]|=0x200;}
        if(i==3){s.cpu.rsp=UINT64_MAX-7;}
        if(i==4){s.binding[1]=0;}
        if(i==5){p.now=300100;}
        if(i==6){c.events=262144;}
        assert(bv_control_stop(&c,&s,&ops,&p)==-1 && !p.call);
    }
    setup(&c,&p,&ops,&s); c.events=262143;
    assert(bv_control_stop(&c,&s,&ops,&p)==1);t=returned(s);
    assert(bv_control_stop(&c,&t,&ops,&p)==1 && c.events==262144);
    assert(bv_control_stop(&c,&s,&ops,&p)==-1);
    setup(&c,&p,&ops,&s);
    assert(bv_control_stop(&c,&s,&ops,&p)==1);
    p.now=300100;t=returned(s);
    assert(bv_control_stop(&c,&t,&ops,&p)==-1 && !p.owned);
    setup(&c,&p,&ops,&s);s.cpu.rip=0xffffffff80123456ULL;
    assert(bv_control_stop(&c,&s,&ops,&p)==0 && !p.call);
    /* Zero initialization is disabled; it must not execute a callback. */
    memset(&c,0,sizeof(c));p.call=0;
    assert(bv_control_stop(&c,&s,&ops,&p)==0 && !p.call);
    puts("BV native return state machine OK");
}
int main(void) { transport_main(); control_tests(); return 0; }
'''


SNAPSHOT_HARNESS = r'''
typedef struct {
    unsigned char ram[12288], shadow[12288], wire[65536];
    size_t used;
    unsigned reads,writes,fail_read,fail_write;
} TraceFixture;
static int trace_read(void *opaque,uint64_t address,unsigned char *out,size_t n)
{
    TraceFixture *t=opaque;
    unsigned index;
    assert(n==4096);
    if(++t->reads==t->fail_read){return 0;}
    if(address==0x10e000){index=0;}
    else if(address==0x110000){index=1;}
    else {assert(address==0x130000);index=2;}
    memcpy(out,t->ram+index*4096,n);return 1;
}
static int trace_write(void *opaque,const unsigned char *bytes,size_t n)
{
    TraceFixture *t=opaque;
    if(++t->writes==t->fail_write){return 0;}
    assert(n<=sizeof(t->wire)-t->used);
    memcpy(t->wire+t->used,bytes,n);t->used+=n;return 1;
}
static void trace_setup(TraceFixture *t,BvSnapshot *snapshot,const BvStop *stop)
{
    BvRange ranges[3]={{0x10e000,1},{0x110000,1},{0x130000,1}};
    memset(t,0,sizeof(*t));memset(snapshot,0,sizeof(*snapshot));
    memset(t->shadow,0xa5,sizeof(t->shadow));
    t->ram[4096]=0xc3;
    bv_le(t->ram+8192,stop->target,8);
    assert(bv_snapshot_init(snapshot,ranges,3,t->shadow,sizeof(t->shadow),
                            trace_write,t));
}
int main(void)
{
    BvControl c;Platform p;BvControlOps ops;BvStop s,a;
    BvSnapshot snapshot;TraceFixture t;unsigned i;
    FILE *f;
    transport_main();control_tests();setup(&c,&p,&ops,&s);
    trace_setup(&t,&snapshot,&s);
    assert(!bv_snapshot_init(&snapshot,snapshot.ranges,3,t.shadow,
                             sizeof(t.shadow),trace_write,&t));
    assert(bv_snapshot_record(&snapshot,0,1,&s,trace_read,trace_write,&t));
    a=returned(s);
    assert(bv_snapshot_record(&snapshot,1,1,&a,trace_read,trace_write,&t));
    /* Direct host write without any guest dirty bit must be recorded. */
    t.ram[8192+32]=0x7f;
    assert(bv_snapshot_record(&snapshot,0,2,&s,trace_read,trace_write,&t));
    assert(bv_snapshot_record(&snapshot,1,2,&a,trace_read,trace_write,&t));
    assert(t.reads==12 && snapshot.sequence==3 && snapshot.phase==0);
    f=fopen("snapshot.bin","wb");assert(f);
    assert(fwrite(t.wire,1,t.used,f)==t.used);assert(!fclose(f));
    for(i=3;i<=34;i++){
        unsigned before_reads;
        assert(bv_snapshot_record(&snapshot,0,i,&s,trace_read,trace_write,&t));
        before_reads=t.reads;
        if(i==33){t.ram[8192+33]=0x6f;}
        assert(bv_snapshot_record(&snapshot,1,i,&a,trace_read,trace_write,&t));
        assert(t.reads==before_reads+(i<=32?3:0));
    }
    f=fopen("cpu-only.bin","wb");assert(f);
    assert(fwrite(t.wire,1,t.used,f)==t.used);assert(!fclose(f));
    for(i=1;i<=3;i++){
        trace_setup(&t,&snapshot,&s);t.fail_read=i;
        assert(!bv_snapshot_record(&snapshot,0,1,&s,trace_read,trace_write,&t));
        assert(snapshot.failed && !snapshot.initialized);
        assert(!bv_snapshot_record(&snapshot,0,1,&s,trace_read,trace_write,&t));
        assert(t.reads==i);
    }
    /* Header, every page descriptor/payload, and trailer short-write failures. */
    for(i=2;i<=9;i++){
        trace_setup(&t,&snapshot,&s);t.fail_write=i;
        assert(!bv_snapshot_record(&snapshot,0,1,&s,trace_read,trace_write,&t));
        assert(snapshot.failed && !snapshot.initialized && t.writes==i);
    }
    trace_setup(&t,&snapshot,&s);snapshot.written=BV_TRACE_LIMIT-223;
    assert(!bv_snapshot_record(&snapshot,0,1,&s,trace_read,trace_write,&t));
    assert(snapshot.failed && !t.reads && t.writes==1);
    trace_setup(&t,&snapshot,&s);
    assert(!bv_snapshot_record(&snapshot,1,1,&s,trace_read,trace_write,&t));
    assert(snapshot.failed && !t.reads);
    trace_setup(&t,&snapshot,&s);
    assert(!bv_snapshot_record(&snapshot,0,2,&s,trace_read,trace_write,&t));
    assert(snapshot.failed && !t.reads);
    assert((bv_crc(UINT32_MAX,(const unsigned char *)"123456789",9)^UINT32_MAX)
            ==UINT32_C(0xcbf43926));
    puts("BV complete-read delta recorder OK");
    return 0;
}
'''


class ObserverTests(unittest.TestCase):
    def test_native_replay_backpressure(self):
        harness=HARNESS.replace('int main(void)','int transport_main(void)')+r'''
int main(void) {
    uint64_t last=0, old; unsigned i;
    assert(bv_replay_yield(NULL,0)==-1);
    for (i=0;i<160;i++) assert(bv_replay_yield(&last,i)==0 && last==0);
    assert(bv_replay_yield(&last,160)==1 && last==160);
    for (i=161;i<=262144;i++) {
        old=last;
        int result=bv_replay_yield(&last,i);
        assert(result==(i-old==64));
        assert(last==(result?i:old) && i-last<64);
    }
    old=last;
    assert(bv_replay_yield(&last,262145)==-1 && last==old);
    assert(bv_replay_yield(&last,last-1)==-1 && last==old);
    last=UINT64_MAX;
    assert(bv_replay_yield(&last,160)==-1 && last==UINT64_MAX);
    puts("BV native replay handoff bounded to64 completed records OK");
    return 0;
}
'''
        self.compile_harness(harness)

    def test_five_site_control(self):
        harness=HARNESS.replace('int main(void)','int transport_main(void)')+\
            CONTROL_HARNESS.replace('int main(void)','int control_main(void)')+r'''
int main(void)
{
    BvControl c;Platform p;BvControlOps ops;BvStop s,t;
    uint64_t sites[5],targets[5];BvStartAck ack={0};unsigned i,j;
    setup(&c,&p,&ops,&s);
    for(i=0;i<3;i++){sites[i]=c.sites[i];targets[i]=c.targets[i];}
    sites[3]=sites[0]+3;sites[4]=sites[0]+4;
    targets[3]=0xffffffff80104000ULL;targets[4]=targets[2];
    memset(&c,0,sizeof(c));
    assert(bv_control_arm_count(&c,sites,targets,5,1,600100,&ops,&p));
    memset(&c,0,sizeof(c));
    assert(!bv_control_arm_count(&c,sites,targets,5,1,600101,&ops,&p));
    assert(!c.state && !c.site_count);
    assert(!bv_control_arm_count(&c,sites,targets,3,1,300101,&ops,&p));
    assert(!c.state && !c.site_count);
    for(i=0;i<5;i++) {
        setup(&c,&p,&ops,&s);memset(&c,0,sizeof(c));
        assert(bv_control_arm_count(&c,sites,targets,5,1,300100,&ops,&p));
        assert(c.site_count==5);
        s.cpu.rip=sites[i];s.target=targets[i];
        s.binding[0]=s.cpu.rip-0xffffffff80000000ULL;
        s.binding[1]=s.target-0xffffffff80000000ULL;
        assert(bv_control_stop(&c,&s,&ops,&p)==1);
        t=returned(s);assert(bv_control_stop(&c,&t,&ops,&p)==1);
        assert(c.events==1 && !c.installed && p.records==2);
        for(j=0;j<17;j++) {
            memset(&c,0,sizeof(c));p.call=p.records=p.arms=p.drops=p.resumes=p.owned=0;
            assert(bv_control_arm_count(&c,sites,targets,5,1,300100,&ops,&p));
            assert(bv_control_stop(&c,&s,&ops,&p)==1);
            t=returned(s);t.cpu.reg[j]^=1;
            assert(bv_control_stop(&c,&t,&ops,&p)==-1 && c.state==BV_CTL_FAILED);
        }
    }
    for(i=0;i<7;i++)if(i!=3 && i!=5) {
        memset(&c,0,sizeof(c));
        assert(!bv_control_arm_count(&c,sites,targets,i,1,300100,&ops,&p));
        assert(!c.state && !c.site_count);
    }
    sites[4]=sites[3];memset(&c,0,sizeof(c));
    assert(!bv_control_arm_count(&c,sites,targets,5,1,300100,&ops,&p));
    sites[4]=sites[0]+4;targets[4]=sites[3];
    assert(!bv_control_arm_count(&c,sites,targets,5,1,300100,&ops,&p));
    for(i=0;i<8;i++) {
        assert(!bv_start_known(&ack,i,1));
        assert(!bv_start_acknowledge(&ack,i,1));
        assert(bv_start_offer(&ack,i,1));
        assert(!bv_start_acknowledge(&ack,i,2));
        assert(bv_start_acknowledge(&ack,i,1));
        assert(bv_start_known(&ack,i,1));
        assert(!bv_start_acknowledge(&ack,i,1));
        assert(!bv_start_offer(&ack,i,1));
        assert(!bv_start_known(&ack,i,2));
        assert(bv_start_offer(&ack,i,2));
        assert(bv_start_acknowledge(&ack,i,2));
        assert(!bv_start_known(&ack,i,1));
        assert(!bv_start_offer(&ack,i,1));
    }
    assert(!bv_start_offer(&ack,8,3));
    assert(!bv_start_offer(&ack,0,0));
    assert(!bv_start_offer(&ack,0,UINT64_C(0x80000000)));
    assert(bv_start_offer(&ack,0,3));
    assert(!bv_start_offer(&ack,1,3)); /* Cannot overwrite an unacknowledged stop. */
    assert(!bv_start_acknowledge(&ack,1,3));
    assert(bv_start_acknowledge(&ack,0,3));
    puts("BV five-site control and exact-generation handoff OK");
    return 0;
}
'''
        self.compile_harness(harness)

    def test_native_five_receipt_replay(self):
        import struct
        import run_qemu_x86_64_large_file as runtime
        import run_qemu_x86_64_boot_programs as boot
        image=ROOT/'build/codex-agent/r83bv-large-file/build06/x86_64/reist-x86_64-bootstrap.elf'
        raw=image.read_bytes();symbols=boot.symbols(image)
        targets=runtime.native_probe_targets(raw,symbols)
        admission=json.loads((ROOT/'build/codex-agent/r83bv-large-file/diagnostic34/native-admission.json').read_text())
        values=[int(v,16) for v in admission['query'].split(':',1)[1].split(';')]
        self.assertEqual(values[0],2)
        self.assertEqual(targets,tuple(values[2:11:2]))
        names=('request','denied','return','start','pio')
        rows=[dict(step=n+1,site=n,pc=symbols['native_session_probe_'+name+'_site64'],
                   target=targets[n],sp=0xffffffff81000000,after_sp=0xffffffff81000008)
              for n,name in enumerate(names)]
        def trace(items):
            return ''.join('NATIVE_STEP_V2 '+json.dumps(r,separators=(',',':'))+'\n' for r in items)+\
                'NATIVE_STEP_END_V2 '+str(len(items))+'\n'
        good=trace(rows)
        self.assertEqual(runtime.validate_native_probe_steps(good,symbols,targets),5)
        for site in range(5):
            for field in rows[site]:
                for value in (True,rows[site][field]^1):
                    altered=[dict(r) for r in rows];altered[site][field]=value
                    with self.assertRaises(ValueError):
                        runtime.validate_native_probe_steps(trace(altered),symbols,targets)
        for bad in (trace(rows[:4]),good+good,good.replace('NATIVE_STEP_V2','COLD_STEP_V1',1),
                    good.replace('NATIVE_STEP_END_V2 5','NATIVE_STEP_END_V2 4')):
            with self.assertRaises(ValueError):runtime.validate_native_probe_steps(bad,symbols,targets)
        for bad in (raw[:51],b'bad'+raw[3:]):
            with self.assertRaises(ValueError):runtime.native_probe_targets(bad,symbols)
        # Mutate the actual mapped RET byte; neither receipt nor map symbol
        # substitution can turn a non-RET source into admitted control evidence.
        phoff=struct.unpack_from('<I',raw,28)[0];count=struct.unpack_from('<H',raw,44)[0]
        address=symbols['native_session_probe_start_site64']-0xffffffff80000000
        positions=[]
        for n in range(count):
            kind,pos,va,pa,length,mem,flags,align=struct.unpack_from('<8I',raw,phoff+n*32)
            if kind==1 and va<=address<va+length:positions.append(pos+address-va)
        self.assertEqual(len(positions),1)
        mutated=bytearray(raw);mutated[positions[0]]=0x90
        with self.assertRaisesRegex(ValueError,'actual RET'):
            runtime.native_probe_targets(bytes(mutated),symbols)

    def test_recorded_native_calibration(self):
        import run_qemu_x86_64_large_file as runtime
        path=os.environ.get("REIST_BV_NATIVE_CALIBRATION")
        if not path:self.skipTest("explicit native calibration evidence required")
        folder=Path(path).resolve()
        self.assertTrue(folder.is_relative_to(ROOT/"build/codex-agent/r83bv-large-file"))
        result=runtime.audit_native_calibration(folder)
        query=json.loads((folder/"native-admission.json").read_text())["query"]
        version=int(query.split(':',1)[1].split(';',1)[0],16)
        self.assertIn(version,(1,2))
        count=32 if version==1 else 160
        self.assertEqual(result["returns"],count)
        self.assertEqual(result["register_values"],count*2*19)
        self.assertFalse(result["qualification"])
        with tempfile.TemporaryDirectory(prefix="native-mutation-",dir=folder.parent) as name:
            mutant=Path(name)
            (mutant/"native-admission.json").write_bytes((folder/"native-admission.json").read_bytes())
            os.link(folder/"native-ram.bin",mutant/"native-ram.bin")
            original=(folder/"native-equivalence.jsonl").read_text()
            rows=[json.loads(line) for line in original.splitlines()]
            rows[0]["after"]["rax"]^=1
            (mutant/"native-equivalence.jsonl").write_text("\n".join(map(json.dumps,rows))+"\n")
            with self.assertRaisesRegex(ValueError,"raw CPU equality"):
                runtime.audit_native_calibration(mutant)
            rows=[json.loads(line) for line in original.splitlines()]
            selected=next(row for row in rows[0]["reads"] if row[1])
            raw=bytearray.fromhex(selected[1]);raw[0]^=1;selected[1]=raw.hex()
            (mutant/"native-equivalence.jsonl").write_text("\n".join(map(json.dumps,rows))+"\n")
            with self.assertRaisesRegex(ValueError,"raw RAM equality"):
                runtime.audit_native_calibration(mutant)

    def test_windows_exclusive_trace_open(self):
        if os.name!="nt":self.skipTest("Windows CRT regression")
        harness=HARNESS.replace("int main(void)","int transport_main(void)")+r'''
#include <errno.h>
#include <fcntl.h>
#include <io.h>
int main(void)
{
    FILE *f;
    int fd,legacy_errno;
    char bytes[4]={0};
    transport_main();
    errno=0;f=fopen("legacy.bin","wbx");legacy_errno=errno;
    printf("legacy wbx result=%d errno=%d\n",f!=NULL,legacy_errno);
    if(f){fclose(f);}
    /* The retained Windows CRT rejects the C11 x mode with EINVAL. */
    assert(!f && legacy_errno==EINVAL);
    fd=open("exclusive.bin",O_WRONLY|O_CREAT|O_EXCL|O_BINARY,0600);
    assert(fd>=0);f=fdopen(fd,"wb");assert(f);
    assert(fwrite("abc",1,3,f)==3 && !fclose(f));
    errno=0;
    assert(open("exclusive.bin",O_WRONLY|O_CREAT|O_EXCL|O_BINARY,0600)<0);
    assert(errno==EEXIST);
    f=fopen("exclusive.bin","rb");assert(f);
    assert(fread(bytes,1,4,f)==3 && !memcmp(bytes,"abc",3) && !fclose(f));
    assert(open("missing-parent/exclusive.bin",O_WRONLY|O_CREAT|O_EXCL|O_BINARY,0600)<0);
    assert(!remove("exclusive.bin"));
    puts("Windows exclusive trace open OK");
    return 0;
}
'''
        # Reproduce the CRT used by the retained observer, not an unrelated
        # PATH compiler (which may use UCRT and support C11 exclusive fopen).
        self.compile_harness(harness, compiler="C:/msys64/mingw64/bin/gcc.exe")

    def test_whpx_timing(self):
        import build_x86_64_large_file_observer as builder
        sources=builder.patched_sources(builder.PATCH.read_text(),builder.SOURCE)
        code=sources['gdbstub/system.c'].split(
            '/* Diagnostic timing only;',1)[1].split('static uint64_t bv_clock',1)[0]
        code=code.split('*/',1)[1]
        harness=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <inttypes.h>
static uint64_t fake_time;
static unsigned reports;
static uint64_t g_get_monotonic_time(void) { return fake_time; }
#define error_report(...) (++reports)
'''+code+r'''
int main(void)
{
    unsigned i;
    fake_time=10; reist_bv_whpx_debug_exit(); bv_timing_complete();
    assert(!bv_exit_us && !reports && !bv_timing_count);
    bv_timing_enabled=true;
    for(i=0;i<256;i++) {
        fake_time=10; reist_bv_whpx_debug_exit();
        bv_notify_us=13; bv_finished_us=20; fake_time=25;
        bv_timing_complete();
    }
    assert(bv_timing_count==256 && reports==1);
    assert(bv_entry_sum==768 && bv_control_sum==1792 && bv_tail_sum==1280);
    fake_time=100; reist_bv_whpx_debug_exit(); bv_timing_complete();
    assert(bv_exit_us==10 && bv_timing_count==256 && reports==1);
    for(i=0;i<4;i++) {
        bv_timing_count=0; bv_timing_enabled=true;
        bv_exit_us=10; bv_notify_us=13; bv_finished_us=20; fake_time=25;
        if(i==0) bv_exit_us=0;
        if(i==1) bv_notify_us=9;
        if(i==2) bv_finished_us=12;
        if(i==3) fake_time=19;
        bv_timing_complete();
        assert(!bv_timing_enabled && !bv_timing_count && reports==i+2);
    }
    return 0;
}
'''
        self.compile_harness(harness)
        path='target/i386/whpx/whpx-all.c'
        restored=sources[path].replace(
            '/* Optional bounded native-observer timing, implemented in gdbstub/system.c. */\n'
            'void reist_bv_whpx_debug_exit(void);\n','').replace(
            '    if (cpu->exception_index == EXCP_DEBUG) {\n'
            '        reist_bv_whpx_debug_exit();\n    }\n\n','')
        self.assertEqual(restored,(builder.SOURCE/path).read_text())

    def test_native_adapter(self):
        import ast
        import run_qemu_x86_64_large_file as runtime
        import build_x86_64_large_file_observer as builder
        original=(ROOT/"build/codex-agent/r83bv-large-file/diagnostic14/observe.gdb").read_text()
        code=runtime.native_observer(original)
        self.assertGreater(code.index("native_query='qreist-native:'"),
                           code.index("binary_reader=BinaryReader("))
        for block in code.split("\npython\n")[1:]:
            ast.parse(block.split("\nend\n",1)[0])
        self.assertIn("native actual target live-register equality",code)
        self.assertIn("native live before-RAM equality",code)
        self.assertIn("CREATE entry stays live",code)
        self.assertIn("hook.enabled=False\n        try:output=gdb.execute('continue'",code)
        self.assertIn("finally:hook.enabled=True",code)
        self.assertIn("native_explicit_steps==before+1",code)
        sampled=runtime.native_observer(original,1024)
        self.assertIn("native-profile.pstats",sampled)
        for block in sampled.split("\npython\n")[1:]:
            ast.parse(block.split("\nend\n",1)[0])
        five=runtime.native_observer(original,8192,five_sites=True)
        self.assertIn('cold_step_count>=8192',five)
        for invalid in (-1,8193,True,1.5):
            with self.assertRaises(ValueError):runtime.native_observer(original,invalid)
        for block in five.split("\npython\n")[1:]:
            ast.parse(block.split("\nend\n",1)[0])
        self.assertNotIn("'COLD_STEP_V1 '",five)
        self.assertIn("'NATIVE_STEP_END_V2 '",five)
        for guard in ('native_five_sites=True','qreist-start:1;',
                      'native_extra_dispatch','native_acknowledged[slot]<gen',
                      'NATIVE_STEP_V2 ','native exact first-start acknowledgement'):
            self.assertIn(guard,five)
        with self.assertRaises(ValueError):runtime.native_observer(code)
        with self.assertRaises(ValueError):runtime.native_observer("bv_batch=1\n"+original)
        sources=builder.patched_sources(builder.PATCH.read_text(),builder.SOURCE)
        system=sources["gdbstub/system.c"]
        for guard in ('g_getenv("REIST_BV_NATIVE")','runstate_is_running()',
                      'bv_breakpoint_count(address) == 0','cpu_get_phys_page_attrs_debug',
                      'bv_control.events < bv_calibration_limit','bv_control.events <= bv_calibration_limit',
                      'bv_live_generation[slot] == gen',
                      'op == 132 || op == 15 || op == 20','exit(78)'):
            self.assertIn(guard,system)
        stop=system.split("static bool bv_native_stop(",1)[1].split(
            "void gdb_handle_reist_native(",1)[0]
        self.assertLess(stop.index("if (i == bv_control.site_count) { return false; }"),
                        stop.index("cpu->singlestep_enabled"))
        self.assertEqual(stop.count("cpu->singlestep_enabled"),2)

    def test_native_five_snapshot(self):
        self.test_native_sparse(extended=True)

    def test_native_sparse(self,extended=False):
        base=HARNESS.replace("int main(void)", "int transport_main(void)")+\
            CONTROL_HARNESS.replace("int main(void)", "int control_main(void)")+\
            SNAPSHOT_HARNESS.replace("int main(void)", "int snapshot_main(void)")
        extra=r'''
static unsigned char tables[5*4096];
static unsigned table_reads, table_failure;
static int read_table(void *p,uint64_t address,unsigned char *out,size_t n)
{
    (void)p;assert(n==4096 && address>=UINT64_C(0x100000000));
    assert(address<UINT64_C(0x100005000));
    if(++table_reads==table_failure) return 0;
    memcpy(out,tables+(size_t)(address-UINT64_C(0x100000000)),n);return 1;
}
int main(void)
{
    uint64_t roots[8]={UINT64_C(0x100000000)};
    unsigned char bits[BV_TRACE_PAGES/8];
    BvSnapshot s={0};TraceFixture t={0};BvControl c;Platform p;
    BvControlOps ops;BvStop before,after;BvRange ranges[3]={{0x10e000,1},{0x110000,1},{0x130000,1}};
    unsigned i;FILE *f;
    bv_le(tables,UINT64_C(0x100001007),8);
    bv_le(tables+4096,UINT64_C(0x100002007),8);
    bv_le(tables+8192+16,UINT64_C(0x100003007),8);
    bv_le(tables+12288+255*8,UINT64_C(0x100004007),8);
    assert(bv_select_tasks(bits,roots,read_table,NULL) && table_reads==4);
    for(i=0;i<32;i++) assert(bits[i]==255);
    assert(bits[32]==31);
    for(i=33;i<sizeof(bits);i++) assert(!bits[i]);
    for(i=0;i<8;i++)roots[i]=UINT64_C(0x100000000);
    table_reads=0;assert(bv_select_tasks(bits,roots,read_table,NULL) && table_reads==32);
    table_reads=0;table_failure=3;assert(!bv_select_tasks(bits,roots,read_table,NULL));
    table_failure=0;tables[0]|=128;assert(!bv_select_tasks(bits,roots,read_table,NULL));
    tables[0]&=~128;tables[0]&=~1;assert(!bv_select_tasks(bits,roots,read_table,NULL));
    tables[0]|=1;
    bv_le(tables+12288+255*8,UINT64_C(0x101000007),8);
    assert(!bv_select_tasks(bits,roots,read_table,NULL));
    assert(!bv_select_frame(bits,UINT64_C(0x100000001)));
    setup(&c,&p,&ops,&before);after=returned(before);
    t.ram[4096]=0xc3;bv_le(t.ram+8192,before.target,8);
    s.sparse=1;
    assert(bv_snapshot_init(&s,ranges,3,t.shadow,sizeof(t.shadow),trace_write,&t));
    for(i=1;i<=4;i++) {
        s.selected[0]=(i&1)?6:7;t.ram[19]=(unsigned char)i;
        assert(bv_snapshot_record(&s,0,i,&before,trace_read,trace_write,&t));
        assert(bv_snapshot_record(&s,1,i,&after,trace_read,trace_write,&t));
    }
    assert(t.reads==20);
    f=fopen("sparse.bin","wb");assert(f);
    assert(fwrite(t.wire,1,t.used,f)==t.used);assert(!fclose(f));
    s.selected[0]=128;
    assert(!bv_snapshot_record(&s,0,5,&before,trace_read,trace_write,&t) && s.failed);
    return 0;
}
'''
        def inspect(folder):
            import io,binascii,struct
            import run_qemu_x86_64_large_file as runtime
            raw=(folder/'sparse.bin').read_bytes()
            self.assertEqual(raw[:8],b'RBVT5\0\0\0' if extended else b'RBVT4\0\0\0')
            sites=(0xffffffff80110000,0xffffffff80110001,0xffffffff80110002)
            targets=(0xffffffff8010eae5,0xffffffff8010eca5,0xffffffff8010ecb3)
            if extended:
                sites+=(0xffffffff80110003,0xffffffff80110004)
                targets+=(0xffffffff80104000,targets[2])
            def reader(data):return runtime.NativeSnapshot(io.BytesIO(data),sites,targets)
            r=reader(raw);first=r.used;first_end=None
            for sequence in range(1,163 if extended else 5):
                for phase in (0,1):
                    row=r.next();self.assertEqual((row['sequence'],row['phase']),(sequence,phase))
                    if first_end is None:first_end=r.used
                    if extended and sequence>160 and phase==1:
                        with self.assertRaises(ValueError):r.memory(sites[0],1)
                        continue
                    self.assertEqual(r.memory(sites[0],1),b'\xc3')
                    if sequence&1:
                        with self.assertRaises(ValueError):r.memory(0xffffffff8010e013,1)
                    else:self.assertEqual(r.memory(0xffffffff8010e013,1),bytes([sequence]))
            for bitmap in (7,4,134):
                bad=bytearray(raw);bad[first+232]=bitmap
                struct.pack_into('<I',bad,first_end-4,binascii.crc32(bad[first:first_end-4]))
                with self.assertRaises(ValueError):reader(bytes(bad)).next()
        if extended:
            base=base.replace('wire[65536]','wire[262144]')
            extra=extra.replace('s.sparse=1;','s.sparse=1;s.extended=1;').replace(
                'i<=4;i++','i<=162;i++').replace('t.reads==20','t.reads==805').replace(
                '&s,0,5,&before','&s,0,163,&before')
        self.compile_harness(base+extra,inspect)

    def test_native_pinned_views(self):
        base=HARNESS.replace("int main(void)", "int transport_main(void)")+\
            CONTROL_HARNESS.replace("int main(void)", "int control_main(void)")
        reference={}
        def compare(folder):
            self.check_snapshot(folder)
            for name in ('snapshot.bin','cpu-only.bin'):
                raw=(folder/name).read_bytes()
                if name not in reference:reference[name]=raw
                self.assertEqual(raw,reference[name])
        self.compile_harness(base+SNAPSHOT_HARNESS,compare)
        view=r'''
static const unsigned char *trace_view(void *opaque,uint64_t address,size_t n)
{
    TraceFixture *t=opaque;
    unsigned index;
    assert(n==4096);
    if(++t->reads==t->fail_read){return NULL;}
    if(address==0x10e000){index=0;}
    else if(address==0x110000){index=1;}
    else {assert(address==0x130000);index=2;}
    return t->ram+index*4096;
}
'''
        variant=SNAPSHOT_HARNESS.replace('static int trace_write(',view+'static int trace_write(')
        variant=variant.replace('bv_snapshot_record(', 'bv_snapshot_record_view(').replace(
            ',trace_read,trace_write,&t)', ',trace_read,trace_view,trace_write,&t)')
        self.compile_harness(base+variant,compare)

    def test_native_snapshot_o0_o2(self):
        self.compile_harness(
            HARNESS.replace("int main(void)", "int transport_main(void)")+
            CONTROL_HARNESS.replace("int main(void)", "int control_main(void)")+
            SNAPSHOT_HARNESS,self.check_snapshot)

    def check_snapshot(self,folder):
        import io,binascii
        import run_qemu_x86_64_large_file as runtime
        wire=(folder/"snapshot.bin").read_bytes()
        self.assertEqual(wire[:8],b"RBVT3\0\0\0")
        sites=(0xffffffff80110000,0xffffffff80110001,0xffffffff80110002)
        targets=(0xffffffff8010eae5,0xffffffff8010eca5,0xffffffff8010ecb3)
        def reader(raw):return runtime.NativeSnapshot(io.BytesIO(raw),sites,targets)
        def replay(raw):
            r=reader(raw)
            for _ in range(4):r.next()
            return r
        r=reader(wire)
        with self.assertRaises(ValueError):r.memory(sites[0],1)
        self.assertEqual(r.next()['phase'],0)
        self.assertEqual(r.memory(sites[0],1),b'\xc3')
        self.assertEqual(r.memory(0xffffffff80130020,1),b'\0')
        with self.assertRaises(ValueError):r.memory(0xffffffff80200000,1)
        r.next();r.next()
        self.assertEqual(r.memory(0xffffffff80130020,1),b'\x7f')
        r.next();self.assertEqual(r.used,len(wire));self.assertEqual(r.sequence,3)
        for offset in (0,8,12,16,24,64,72,80,288,296,len(wire)-1):
            bad=bytearray(wire);bad[offset]^=1
            with self.assertRaises(ValueError):replay(bad)
        for n in (0,15,63,64,65,len(wire)-1):
            with self.assertRaises(ValueError):replay(wire[:n])
        first=64;second=first+232+3*4112+32
        self.assertEqual(len(wire),second+3*264+80,
                         "one host byte change occupies one64-byte block")
        # Valid checksums on corrupted after-state must still fail independently.
        for field in range(2,27):
            bad=bytearray(wire);bad[second+8+field*8]^=1
            struct.pack_into('<I',bad,second+260,
                             binascii.crc32(bad[second:second+260]))
            r=reader(bad);r.next();saved=bytes(r.ram)
            with self.assertRaises(ValueError):r.next()
            self.assertTrue(r.failed);self.assertEqual(bytes(r.ram),saved)
            with self.assertRaises(ValueError):r.next()
        # A complete CRC cannot excuse a missing initial page.
        bad=bytearray(wire)
        del bad[first+232:first+232+4112]
        end=second-4112
        struct.pack_into('<I',bad,end-8,2)
        struct.pack_into('<I',bad,end-4,binascii.crc32(bad[first:end-4]))
        with self.assertRaises(ValueError):reader(bad).next()
        for mask in (0,0xfffffffffffffffe):
            bad=bytearray(wire)
            struct.pack_into('<Q',bad,first+232+8,mask)
            with self.assertRaisesRegex(ValueError,"block mask"):reader(bad).next()
        third=second+264
        bad=bytearray(wire)
        struct.pack_into('<Q',bad,third+232+8,0)
        r=reader(bad);r.next();r.next();saved=bytes(r.ram)
        with self.assertRaisesRegex(ValueError,"block mask"):r.next()
        self.assertEqual(bytes(r.ram),saved)
        for offset in (first+224,second+224):
            bad=bytearray(wire);bad[offset]=0
            with self.assertRaisesRegex(ValueError,"availability flag"):replay(bad)
        extended=(folder/"cpu-only.bin").read_bytes()
        r=reader(extended)
        for _ in range(64):r.next()
        r.next()
        self.assertEqual(r.memory(0xffffffff80130021,1),b"\0")
        cpu_only_offset=r.used
        self.assertEqual(r.next()["phase"],1)
        self.assertFalse(r.ram_current)
        with self.assertRaises(ValueError):r.memory(0xffffffff80130021,1)
        r.next()
        self.assertEqual(r.memory(0xffffffff80130021,1),b"\x6f",
                         "next full record rereads a host write after the prior full record")
        r.next()
        with self.assertRaises(ValueError):r.memory(sites[0],1)
        bad=bytearray(extended);bad[cpu_only_offset+224]=1
        r=reader(bad)
        for _ in range(65):r.next()
        with self.assertRaisesRegex(ValueError,"availability flag"):r.next()

    def test_native_control_o0_o2(self):
        self.compile_harness(HARNESS.replace("int main(void)", "int transport_main(void)")
                             + CONTROL_HARNESS)

    def test_client_response_mutations(self):
        import run_qemu_x86_64_large_file as runtime
        spans=((0xffff800100000001,3),(0xffffffff80100002,2))
        wire=b"RBV1"+struct.pack("<QHH",1,2,5)
        wire+=struct.pack("<QI",spans[0][0],3)+b"abc"
        wire+=struct.pack("<QI",spans[1][0],2)+b"de"
        calls=[]
        def packet(request):
            calls.append(request)
            return wire.hex().encode()
        reader=runtime.BatchRAM(packet)
        self.assertEqual(reader.read(spans),(b"abc",b"de"))
        self.assertEqual(calls,["qreist-mem:1;1;2;ffff800100000001,3;ffffffff80100002,2"])
        # Stale sequence is fatal. Never retry the same connection after failure.
        with self.assertRaises(ValueError):reader.read(spans)
        self.assertTrue(reader.failed)
        with self.assertRaises(ValueError):reader.read(spans)
        self.assertEqual(len(calls),2)
        for offset in (0,4,12,14,16,24,31,39):
            altered=bytearray(wire);altered[offset]^=1
            broken=runtime.BatchRAM(lambda request:bytes(altered).hex().encode())
            with self.assertRaises(ValueError):broken.read(spans)
            self.assertTrue(broken.failed);self.assertEqual(broken.sequence,0)
        for reply in (wire[:-1].hex().encode(),wire.hex().encode()+b"00",
                      b"E14",b"x"*len(wire)*2,wire.hex().upper().encode(),wire.hex()):
            broken=runtime.BatchRAM(lambda request:reply)
            with self.assertRaises(ValueError):broken.read(spans)
            self.assertTrue(broken.failed)
        invalid=((),list(spans),tuple(reversed(spans)),
                 ((spans[0][0],0),),((spans[0][0],1537),),((0,1),),
                 ((0xffffffff87ffffff,2),),((spans[0][0],True),),
                 ((spans[0][0],4),(spans[0][0]+3,1)))
        for request in invalid:
            calls.clear();broken=runtime.BatchRAM(packet)
            with self.assertRaises(ValueError):broken.read(request)
            self.assertFalse(calls)

    def test_batch_observer_binding(self):
        import ast
        import run_qemu_x86_64_large_file as runtime
        binding=os.environ.get("REIST_BV_OBSERVER_BINDING")
        if not binding:self.skipTest("explicit isolated QEMU binding required")
        executable,firmware=runtime.observer_toolchain(binding)
        self.assertTrue(executable.is_file());self.assertTrue(firmware.is_dir())
        original_binding=json.loads(Path(binding).read_text())
        for field,value,reason in (
            ("dlls",{},"complete accepted DLL set"),
            ("observer_sources",{},"complete staged source set"),
            ("observer_version",True,"tool binary/patch binding"),
        ):
            altered=dict(original_binding);altered[field]=value
            with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",suffix=".json",
                                              dir=Path(binding).parent,delete=False) as stream:
                json.dump(altered,stream)
                mutation=Path(stream.name)
            try:
                with self.assertRaisesRegex(ValueError,reason):runtime.observer_toolchain(mutation)
            finally:mutation.unlink()
        original=(ROOT/"build/codex-agent/r83bv-large-file/diagnostic14/observe.gdb").read_text()
        code=runtime.batch_observer(original)
        self.assertIn("BV exact stopped RAM equivalence",code)
        self.assertIn("static probe forbids QMP/large reads",code)
        self.assertIn("actual single RET target hit",code)
        # Both generated Python blocks must remain executable Python.
        blocks=code.split("\npython\n")[1:]
        self.assertGreaterEqual(len(blocks),2)
        for block in blocks:ast.parse(block.split("\nend\n",1)[0])

    def test_stopped_qemu_transport(self):
        """No guest instruction runs: compare new RAM packets to standard RSP."""
        import build_x86_64_large_file_observer as builder
        binding_path = os.environ.get("REIST_BV_OBSERVER_BINDING")
        if not binding_path:
            self.skipTest("explicit isolated QEMU binding required")
        binding = json.loads(Path(binding_path).read_text())
        self.assertEqual(builder.sha(binding["executable"]), binding["sha256"])
        self.assertEqual(builder.sha(builder.PATCH), binding["observer_patch"])
        for enabled in ("0", "1"):
            with socket.socket() as reserve:
                reserve.bind(("127.0.0.1", 0))
                port = reserve.getsockname()[1]
            command = [binding["executable"], "-machine", "pc,accel=whpx", "-m", "128M",
                       "-S", "-nodefaults", "-display", "none", "-monitor", "none",
                       "-serial", "none", "-no-reboot", "-nic", "none",
                       "-L", binding["firmware_directory"],
                       "-gdb", f"tcp:127.0.0.1:{port}"]
            env = dict(os.environ, REIST_BV_OBSERVER=enabled)
            env.pop("REIST_BV_NATIVE",None)
            env.pop("REIST_BV_NATIVE_TRACE",None)
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.PIPE, env=env)
            connection = None
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    try:
                        connection = socket.create_connection(("127.0.0.1", port), timeout=1)
                        break
                    except OSError:
                        if process.poll() is not None:
                            self.fail("QEMU startup: " + process.stderr.read().decode(errors="replace"))
                        time.sleep(.02)
                self.assertIsNotNone(connection, "bounded QEMU startup")
                connection.settimeout(3)

                def byte():
                    data = connection.recv(1)
                    self.assertEqual(len(data), 1, "complete RSP frame")
                    return data

                def packet(value):
                    raw = value.encode("ascii")
                    connection.sendall(b"$" + raw + b"#" + f"{sum(raw)&255:02x}".encode())
                    self.assertEqual(byte(), b"+")
                    self.assertEqual(byte(), b"$")
                    reply = bytearray()
                    for _ in range(4096):
                        data = byte()
                        if data == b"#":
                            break
                        reply.extend(data)
                    else:
                        self.fail("RSP response capacity")
                    checksum = byte() + byte()
                    self.assertEqual(int(checksum, 16), sum(reply) & 255)
                    connection.sendall(b"+")
                    return bytes(reply)

                query = "qreist-mem:1;1;2;ffffffff80100000,10;ffffffff80100020,10"
                self.assertEqual(packet("qreist-native:1;1;2;3;4;5;6;7;8;9"),b"E22")
                if enabled == "0":
                    self.assertEqual(packet(query), b"E22")
                    continue
                self.assertEqual(packet("Qqemu.PhyMemMode:1"), b"OK")
                first = bytes.fromhex(packet("m100000,10").decode())
                second = bytes.fromhex(packet("m100020,10").decode())
                expected = b"RBV1" + struct.pack("<QHH", 1, 2, 32)
                expected += struct.pack("<QI", 0xffffffff80100000, 16) + first
                expected += struct.pack("<QI", 0xffffffff80100020, 16) + second
                self.assertEqual(bytes.fromhex(packet(query).decode()), expected)
                self.assertEqual(packet(query), b"E22")  # no replay
                # Valid profile address but absent RAM: no MMIO fallback/sequence consumption.
                self.assertEqual(packet("qreist-mem:1;2;1;ffff800100000000,1"), b"E14")
                self.assertEqual(packet("qreist-mem:1;2;1;ffffffff80100000,0"), b"E22")
                result = bytes.fromhex(packet("qreist-mem:1;2;1;ffffffff80100000,10").decode())
                self.assertEqual(result, b"RBV1" + struct.pack("<QHHQI", 2, 1, 16,
                                                                        0xffffffff80100000, 16) + first)
                self.assertEqual(packet("m100000,10"), first.hex().encode())
            finally:
                if connection is not None:
                    connection.close()
                if process.poll() is None:
                    process.terminate()
                process.communicate(timeout=5)
                self.assertIsNotNone(process.poll(), "owned QEMU cleanup")

    def test_exact_isolated_patch(self):
        import build_x86_64_large_file_observer as builder
        patch = builder.PATCH.read_text()
        before = {name: builder.sha(builder.SOURCE/name) for name in builder.FILES[:2]}
        result = builder.patched_sources(patch, builder.SOURCE)
        self.assertEqual(result["gdbstub/reist-observer.h"], transport_header())
        self.assertIn("memory_region_is_ram_device(region)", result["gdbstub/system.c"])
        self.assertEqual(before, {name: builder.sha(builder.SOURCE/name)
                                  for name in builder.FILES[:2]})
        for changed in (
            patch.replace("+++ b/gdbstub/system.c", "+++ b/../system.c"),
            patch.replace(" static const GdbCmdParseEntry", " broken const GdbCmdParseEntry", 1),
            patch + patch,
            patch.replace("--- /dev/null", "--- a/unknown", 1),
        ):
            with self.assertRaises(ValueError):
                builder.patched_sources(changed, builder.SOURCE)

    def test_actual_transport_o0_o2(self):
        self.compile_harness(HARNESS)

    def compile_harness(self, harness, inspect=None, compiler="gcc"):
        from measure_cpp_baseline import suppress_windows_test_dialogs
        suppress_windows_test_dialogs()
        base = ROOT / "build/codex-agent/r83bv-large-file"
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="observer-host-", dir=base) as name:
            folder = Path(name)
            (folder / "reist-observer.h").write_text(transport_header(), encoding="utf-8")
            source = folder / "host.c"
            source.write_text(harness, encoding="utf-8")
            for optimization in ("-O0", "-O2"):
                exe = folder / (optimization[1:] + ".exe")
                for command in (
                    [compiler, "-std=c11", optimization, "-Wall", "-Wextra", "-Werror",
                     str(source), "-o", str(exe)],
                    [str(exe)],
                ):
                    result = subprocess.run(command, capture_output=True, timeout=60,
                                            cwd=folder)
                    self.assertEqual(result.returncode, 0,
                                     (result.stdout + result.stderr).decode(errors="replace"))
                if inspect:inspect(folder)


if __name__ == "__main__":
    unittest.main()
