"""Bounded, private-image FAT32 object/repair campaign with an independent disk oracle.

The private observer reports plans, not expected disk bytes. The host derives
each permitted after-image from file semantics, checks every journal target,
and reconstructs the complete medium including retained undo slots. No fault
opcode, path or observer is installed in the reference image.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import struct
import subprocess
import threading
import time
import zlib
from pathlib import Path

import build_user_program as builder
from build_system_programs import PROGRAMS
from create_native_boot_image import write_fat32_volume
from measure_cpp_baseline import suppress_windows_test_dialogs
from run_qemu_math import ROOT, kernel_digest
from verify_fat32_write_artifacts import RESCUE_FILES, validate_rescue_sizes
import run_qemu_journal_handoff as handoff
import run_qemu_fat32_recovery_admission as recovery
import run_qemu_smoke as smoke

ALLOWED = ROOT / "build/codex-agent/r342-fat32-write"
DATA = recovery.DATA_START
SIZE = 4*1024*1024+17
PATH = "/mnt/hdd1/target.bin"
CASES = ("normal", "fault", "hang", "cancel", "lost-reply", "repair-cut", "exhaust")


def object_keys(command):
    if len(command)>256: raise ValueError("private command quota")
    keys=[]
    for character in command:
        if "A"<=character<="Z": keys.append("sendkey shift-"+character.lower()+"\n")
        else: keys.extend(handoff.handoff_keys(character)[:-1])
    return keys+["sendkey ret\n"]


def put32(data, offset, value):
    struct.pack_into("<I", data, offset, value)


def get32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def header(state, sequence, entries=()):
    result = bytearray(recovery.header_v2(state, entries))
    put32(result, 12, sequence)
    put32(result, 20, 0)
    put32(result, 20, zlib.crc32(result))
    return bytes(result)


def fixture(path, size=SIZE):
    raw = bytearray(recovery.expected_disk(recovery.create_disk(path, "v2"), "v2"))
    # No pre-existing journal evidence is silently accepted as our baseline.
    raw[8*512:32*512] = bytes(24*512)
    raw[8*512:9*512] = raw[31*512:32*512] = header(0, 7)
    raw[32*512:DATA*512] = bytes((DATA-32)*512)
    chain = [3+rank*7 for rank in range((size+511)//512)]
    if chain and chain[-1] >= 65527: raise ValueError("fixture capacity")
    for copy in (32, 544):
        for cluster, link in ((0, 0xffffff8), (1, 0xfffffff), (2, 0xfffffff)):
            put32(raw, copy*512+cluster*4, 0xa0000000 | link)
        for index, cluster in enumerate(chain):
            put32(raw, copy*512+cluster*4, 0xa0000000 | (chain[index+1] if index+1 < len(chain) else 0xfffffff))
    root = DATA*512
    raw[root:root+512] = bytes(512)
    raw[root:root+11] = b"TARGET  BIN"
    raw[root+11] = 0x20
    struct.pack_into("<H", raw, root+26, chain[0] if chain else 0)
    put32(raw, root+28, size)
    for rank, cluster in enumerate(chain):
        offset = (DATA+cluster-2)*512
        raw[offset:offset+512] = bytes(((rank*512+i)*13+61)&255 for i in range(512))
    path.write_bytes(raw)
    return bytes(raw)


class DiskOracle:
    """Independent regular-file semantics; never imports the candidate planner."""
    def __init__(self, initial):
        if len(initial) != recovery.TOTAL_SECTORS*512: raise ValueError("oracle geometry")
        self.raw = bytearray(initial)
        self.sequence = 7
        self.plans = 0
        self.flushes = 0
        self.data_progress = {1: 0, 4: 0}
        self.last_before = None
        self.last_undo = None
        self.last_targets = None

    def chain(self):
        cluster = struct.unpack_from("<H", self.raw, DATA*512+26)[0]
        cluster |= struct.unpack_from("<H", self.raw, DATA*512+20)[0] << 16
        seen, result = set(), []
        while cluster:
            if cluster in seen or not 2 <= cluster < 65527: raise ValueError("oracle chain")
            seen.add(cluster); result.append(cluster)
            cluster = get32(self.raw, 32*512+cluster*4) & 0xfffffff
            if cluster >= 0xffffff8: return result
            if len(result) > 65525: raise ValueError("oracle work bound")
        return result

    def apply(self, values):
        # kind,offset,bytes,old_size,new_size,released,nalloc,alloc...,ntarget,target...
        if len(values) < 8: raise ValueError("short plan record")
        kind, offset, length, old_size, size, released, nalloc = values[:7]
        if nalloc > 20 or len(values) < 8+nalloc: raise ValueError("allocation quota")
        allocated = values[7:7+nalloc]
        targets = values[8+nalloc:]
        if values[7+nalloc] != len(targets) or len(targets) > 20 or len(set(targets)) != len(targets):
            raise ValueError("target quota/duplicate")
        if old_size != get32(self.raw, DATA*512+28) or not 0 <= size <= 0xffffffff:
            raise ValueError("size correlation")
        before = bytes(self.raw)
        chain = self.chain()
        changed = set()
        permitted = set()
        def fat(cluster, value):
            for copy in (32, 544):
                pos = copy*512+cluster*4
                put32(self.raw, pos, (get32(self.raw, pos)&0xf0000000)|value)
                permitted.add(pos//512)
        if kind == 1:
            if allocated or released or size != old_size or not 0 < length <= 20*512-offset%512 or offset+length > old_size:
                raise ValueError("overwrite semantics")
            # The only overwrite in the fixed exercise starts at byte3.
            if offset != 3+self.data_progress[1] or self.data_progress[1]+length > 131072:
                raise ValueError("overwrite input correlation")
        elif kind in (3, 4):
            if offset != old_size or released or size != old_size+length or not 0 < length <= 20*512:
                raise ValueError("growth semantics")
            expected_count = (size+511)//512-len(chain)
            if nalloc != expected_count or len(set(allocated)) != nalloc:
                raise ValueError("allocation count")
            for cluster in allocated:
                if not 3 <= cluster < 65527 or get32(before, 32*512+cluster*4)&0xfffffff:
                    raise ValueError("non-free allocation")
                if chain: fat(chain[-1], cluster)
                chain.append(cluster); fat(cluster, 0xfffffff)
            if kind == 4 and self.data_progress[4]+length > 4097: raise ValueError("append input correlation")
            if kind == 3 and size > SIZE+12290: raise ValueError("resize target exceeded")
        elif kind == 2:
            if allocated or length or not 0 <= released <= len(chain) or size > old_size or size < 513:
                raise ValueError("shrink semantics")
            retained = len(chain)-released
            if retained != (size+511)//512 or (size != 513 and size != retained*512):
                raise ValueError("orphan/partial shrink")
            for cluster in chain[retained:]: fat(cluster, 0)
            chain = chain[:retained]
            if chain: fat(chain[-1], 0xfffffff)
        elif kind == 5:
            if length or allocated or released or targets or size != old_size: raise ValueError("sync effects")
            self.flushes += 1
            return
        else: raise ValueError("unknown planner kind")
        if kind in (1, 3, 4):
            for i in range(length):
                position = offset+i
                sector = DATA+chain[position//512]-2
                value = 0 if kind == 3 else ((self.data_progress[kind]+i)*17+23)&255
                self.raw[sector*512+position%512] = value
                permitted.add(sector)
            if kind in self.data_progress: self.data_progress[kind] += length
        if kind != 1:
            root = DATA*512
            first = chain[0] if chain else 0
            struct.pack_into("<H", self.raw, root+20, first >> 16)
            struct.pack_into("<H", self.raw, root+26, first & 65535)
            put32(self.raw, root+28, size); permitted.add(DATA)
            if allocated or released:
                # Fixture has exactly one valid FSInfo with unknown hints.
                put32(self.raw, 512+488, 0xffffffff); put32(self.raw, 512+492, 0xffffffff)
                permitted.add(1)
        for sector in permitted:
            if self.raw[sector*512:(sector+1)*512] != before[sector*512:(sector+1)*512]: changed.add(sector)
        if not changed.issubset(targets) or not set(targets).issubset(permitted) or not targets:
            raise ValueError("missing/foreign journal target")
        self.last_before = before
        self.last_targets = targets
        entries = [(sector, before[sector*512:(sector+1)*512]) for sector in targets]
        for index, (_, undo) in enumerate(entries): self.raw[(9+index)*512:(10+index)*512] = undo
        self.sequence += 1
        self.raw[8*512:9*512] = self.raw[31*512:32*512] = header(0, self.sequence)
        self.last_undo = entries
        self.plans += 1; self.flushes += 4

    def rollback(self, active=False):
        if self.plans != 1 or self.last_before is None: raise ValueError("fault must hit first transaction")
        if active:
            self.raw[8*512:9*512] = self.raw[31*512:32*512] = header(1, self.sequence, self.last_undo)
        else:
            for sector, undo in self.last_undo: self.raw[sector*512:(sector+1)*512] = undo
        return bytes(self.raw)


def plan_records(text):
    records = []
    pending = None
    for line in text.replace("\r", "").splitlines():
        if line == "R342_PRIVATE_PLAN_BEGIN":
            if pending is not None: raise ValueError("nested private plan")
            pending = []
        elif line.startswith("R342_PRIVATE_VALUES "):
            fields = line.split()[1:]
            if pending is None or not 1 <= len(fields) <= 4 or any(not f.isascii() or not f.isdecimal() or int(f)>0xffffffff for f in fields):
                raise ValueError("malformed private values")
            pending.extend(map(int, fields))
            if len(pending)>49: raise ValueError("private plan capacity")
        elif line == "R342_PRIVATE_PLAN_END":
            if pending is None: raise ValueError("unpaired private plan end")
            records.append(pending); pending = None
        if line.startswith("R342_PRIVATE_PLAN "):
            fields = line.split()[1:]
            if len(fields) > 49 or any(not f.isascii() or not f.isdecimal() or int(f) > 0xffffffff for f in fields):
                raise ValueError("malformed private plan")
            records.append(list(map(int, fields)))
    if pending is not None or not records or len(records) > 256: raise ValueError("missing/excess plan records")
    return records


def private_stats(text):
    records = re.findall(r"^R342_PRIVATE_STATS ([^\r\n]+)\r?$",text,re.M)
    if len(records)!=1: raise ValueError("missing/duplicate private stats")
    fields=records[0].split()
    if len(fields)!=12 or any(not f.isascii() or not f.isdecimal() or int(f)>0xffffffff for f in fields):
        raise ValueError("invalid private stats")
    return list(map(int,fields))


def private_source(source, mode):
    if mode not in range(len(CASES)) or "R342_PRIVATE_" in source: raise ValueError("private source identity")
    changes = []
    def before(anchor, extra):
        if source.count(anchor) != 1: raise ValueError("private anchor drift: "+anchor[:80])
        changes.append((source.index(anchor), extra))
    # Storage has NO terminal capability. Store bounded observations locally;
    # a private read-only request lets the foreground test print them after IO.
    before("static int vfs_write_transfer(", """/* R342_PRIVATE_PLAN: read-only observer, not a Storage console grant. */
static uint32_t r342_records[256][64], r342_count;
static uint32_t r342_stats[12], r342_flushes;
static void r342_plan(vfs_write_job_t* j) {
    if(r342_count>=256) return;
    uint32_t *record=r342_records[r342_count++], *p=record+1;
    reist_fat32_overwrite_t* w=&j->plan.overwrite;
    uint32_t size=vfs_write_proof.view.file_size, released=0, n=0;
    if(j->kind==2){size=j->plan.shrink.resulting_size;released=j->plan.shrink.released;}
    if(j->kind==3 || j->kind==4){size=j->plan.grow.resulting_view.file_size;n=j->plan.grow.allocated_count;}
    *p++=j->kind;*p++=w->offset;*p++=w->bytes;
    *p++=vfs_write_proof.view.file_size;*p++=size;*p++=released;*p++=n;
    for(unsigned i=0;i<n && i<20;++i)*p++=j->plan.grow.allocated[i];
    *p++=w->target_count;for(unsigned i=0;i<w->target_count && i<20;++i)*p++=w->targets[i];
    record[0]=(uint32_t)(p-record-1);r342_flushes=0;
}
""")
    before("    return vfs_write_finish_plan(job);", "    r342_plan(job);\n")
    before('            x86os_puts("STORAGE REPAIR_QUALIFIED resource=");',
           "            r342_stats[11] |= 1U << job->request.resource;\n")
    before("        if (request.operation == X86OS_STORAGE_VFS_SHADOW_STAT &&\n", """        if(request.operation==X86OS_STORAGE_VFS_SHADOW_STAT && request.length==512 &&
           ((uint32_t*)data)[0]==0x3427ACE1U && ((uint32_t*)data)[1]<257U) {
            uint32_t index=((uint32_t*)data)[1];
            vfs_object_zero(data,512);
            uint32_t *out=(uint32_t*)data;out[0]=0x3427ACE2U;out[1]=r342_count;
            if(index<r342_count)for(unsigned i=0;i<64;++i)out[i+2]=r342_records[index][i];
            for(unsigned i=0;i<12;++i)out[66+i]=r342_stats[i];
            int done=x86os_storage_complete(request.handle,0,data);
            if(done && done!=-22 && done!=-125 && done!=-110)return 3;
            continue;
        }
""")
    before("    if (job->phase == 1U) {", "    ++r342_stats[0]; if(job->phase==1U)++r342_stats[1];\n")
    transfer_anchor = "    return status ? status : x86os_storage_journal_io(request, data);\n"
    start = source.index("static int vfs_write_transfer(")
    end = source.index("static bool vfs_write_probe_read(", start)
    if source[start:end].count(transfer_anchor) != 1: raise ValueError("private transfer drift")
    position = start+source[start:end].index(transfer_anchor)
    observation = """    uint64_t before=0,after=0;x86os_monotonic_ms(&before);
    int result=status ? status : x86os_storage_journal_io(request,data);
    x86os_monotonic_ms(&after);r342_stats[2]+=(uint32_t)(after-before);
    if(((vfs_write_job_t*)context)->kind==2U && (request->operation==1U || request->operation==2U))
        r342_stats[request->operation==1U ? 3U : 7U]+=(uint32_t)(after-before);
    if(request->operation>=1U && request->operation<=3U)r342_stats[7+request->operation]+=(uint32_t)(after-before);
    if(!result && request->operation<8U)++r342_stats[3+request->operation];
"""
    replacement = observation+"    return result;\n"
    if mode:
        cut = "__asm__ volatile(\"movl $0x342FA017, %%eax; ud2\" ::: \"eax\");"
        if mode == 2: cut = "for(;;) __asm__ volatile(\"pause\");"
        if mode == 3:
            cut = """uint64_t now=0; x86os_monotonic_ms(&now);
            if(now<((vfs_write_job_t*)context)->deadline)x86os_sleep_ms((uint32_t)(((vfs_write_job_t*)context)->deadline-now));
            int denied=x86os_storage_journal_io(request,data);
            if(denied<0) __asm__ volatile("movl $0x342FA019, %%eax; ud2" ::: "eax");
            else __asm__ volatile("movl $0x342FA01A, %%eax; ud2" ::: "eax");
            return -110;"""
        if mode == 4: cut = ""  # delay only after the complete durable transaction, below
        replacement = observation+"""
    if (!result && request->operation==REIST_STORAGE_JOURNAL_FLUSH && ++r342_flushes==3 &&
        ((vfs_write_job_t*)context)->transaction.journal.sequence==8U) {
        CUT
    }
    return result;
""".replace("CUT\n", cut+"\n")
        # Store a replacement separately; reconstruction below checks it exactly.
        if mode == 4:
            before("    int completed = x86os_storage_complete(job->request.handle, 0, (const uint8_t *)&job->frame);", """    if(job->frame.operation==REIST_VFS_WRITE_DATA && job->transaction.journal.sequence==8U &&
       r->outcome==REIST_FILE_OBJECT_DURABLE_COMMIT) {
        uint64_t now=0; x86os_monotonic_ms(&now);
        if(now<job->deadline)x86os_sleep_ms((uint32_t)(job->deadline-now));
    }
""")
        if mode in (5, 6):
            anchor = "    return vfs_repair_write_many(context, base, sector, 1, data, master);"
            # The first reverse-restored target is cluster136, LBA1190.
            before(anchor, """    if(sector==1190U) {
        uint8_t old[512]; bool changed=vfs_repair_read(context,base,sector,old,master) && !format_equal(old,data,512);
        bool ok=vfs_repair_io(context,REIST_STORAGE_JOURNAL_WRITE_DEFERRED,sector,1U,(void*)data);
        if(ok && (ALWAYS || changed)) {
            __asm__ volatile("movl $0x342FA018, %%eax; ud2" ::: "eax");}
        return ok;
    }
""".replace("ALWAYS", "1" if mode == 6 else "0"))
    changes.append((position, (transfer_anchor, replacement)))
    result = source
    for pos, edit in sorted(changes, key=lambda x: x[0], reverse=True):
        if isinstance(edit, tuple): result = result[:pos]+edit[1]+result[pos+len(edit[0]):]
        else: result = result[:pos]+edit+result[pos:]
    restored = result
    for _, edit in changes:
        old, new = edit if isinstance(edit, tuple) else ("", edit)
        if restored.count(new) != 1: raise ValueError("private inverse ambiguity")
        restored = restored.replace(new, old, 1)
    if restored != source: raise ValueError("private source roundtrip")
    return result


def private_client_source(source, *, exhaust=False):
    anchor = "int main(int argc, char** argv) {"
    end = "    return result ? stage : 0;"
    if source.count(anchor)!=1 or source.count(end)!=1 or "R342_PRIVATE_" in source:
        raise ValueError("private client anchor drift")
    helper = """static int r342_root_read(void) {
    /* Private proof of the pre-existing rescue read path, NOT a fallback in
     * file-object clients and not authority to restart the exhausted service. */
    char bytes[512]; uint32_t used=0; int result=0,complete=0;
    uint64_t start=0,now=0,last=0;
    if(x86os_monotonic_ms(&start))return -5;
    last=start;
    int fd=x86os_open_flags("/htdocs/hello.js",X86OS_O_RDONLY);
    if(fd<0)return fd;
    for(unsigned step=0;step<=sizeof(bytes);++step) {
        if(x86os_monotonic_ms(&now) || now<last || now-start>=5000){result=-110;break;}
        last=now;
        int count=x86os_read(fd,bytes+used,sizeof(bytes)-used);
        if(count<0 || (uint32_t)count>sizeof(bytes)-used){result=-5;break;}
        if(!count){complete=1;break;}
        used+=(uint32_t)count;
        if(used==sizeof(bytes)){result=-75;break;}
    }
    if(x86os_close(fd)<0)result=-5;
    if(result || !complete)return result ? result : -75;
    for(uint32_t i=0;i<used;++i)x86os_putchar(bytes[i]);
    x86os_puts("\\nR342_PRIVATE_ROOT_READ_OK\\n");return 0;
}
static int r342_dump(void) {
    uint64_t start=0,now=0;if(x86os_monotonic_ms(&start))return -5;
    for(uint32_t index=0;index<256;++index) {
        uint32_t data[128]={0};data[0]=0x3427ACE1U;data[1]=index;
        x86os_storage_submit_t q={X86OS_STORAGE_REQUEST_VERSION,sizeof(q),X86OS_STORAGE_VFS_SHADOW_STAT,0,0,512,5000};
        x86os_storage_handle_t h=0;int status=x86os_storage_submit(&q,data,&h);
        if(status || !h)return status ? status : -5;
        for(;;) {
            if(x86os_monotonic_ms(&now) || now<start || now-start>=5000){x86os_storage_cancel(h);return -110;}
            int32_t result=0;status=x86os_storage_collect(h,&result,(uint8_t*)data);
            if(!status){if(result)return result;break;}
            if(status!=-11){x86os_storage_cancel(h);return status;}
            x86os_sleep_ms(1);
        }
        if(data[0]!=0x3427ACE2U || data[1]>256 || data[2]>49)return -84;
        if(!index) {
            x86os_puts("R342_PRIVATE_STATS");
            for(unsigned i=0;i<12;++i){x86os_putchar(' ');decimal(data[66+i]);}x86os_putchar('\\n');
        }
        if(index>=data[1])return 0;
        x86os_puts("R342_PRIVATE_PLAN_BEGIN\\n");
        for(unsigned i=0;i<data[2];++i) {
            if(!(i%4))x86os_puts("R342_PRIVATE_VALUES");
            x86os_putchar(' ');decimal(data[3+i]);
            if(i%4==3 || i+1==data[2])x86os_putchar('\\n');
        }
        x86os_puts("R342_PRIVATE_PLAN_END\\n");
    }
    return -75;
}
"""
    if exhaust:
        helper += """static int r342_wait_root(void) {
    uint64_t start=0,now=0,last=0;if(x86os_monotonic_ms(&start))return -5;
    last=start;x86os_puts("R342_PRIVATE_ROOT_WAIT\\n");
    for(unsigned step=0;step<5000;++step) {
        if(x86os_monotonic_ms(&now) || now<last || now-start>=5000)return -110;
        last=now;char key=0;int count=x86os_read(0,&key,1);
        if(count==1)return key=='r' ? r342_root_read() : -22;
        if(count!=-11)return -5;
        x86os_sleep_ms(1);
    }
    return -110;
}
"""
    trailer = "    int trace=r342_dump();x86os_puts(\"R342_PRIVATE_DUMP result=\");x86os_print_number(trace);x86os_putchar('\\n');\n"
    if exhaust:
        trailer += '    if(result && r342_wait_root())x86os_puts("R342_PRIVATE_ROOT_READ_FAIL\\n");\n'
    observe = '''
    if(argc==2 && equal(argv[1],"--r342-root-read"))return r342_root_read();
    if(argc==2 && equal(argv[1],"--r342-observe")) {
        int trace=r342_dump();x86os_puts("R342_PRIVATE_DUMP result=");
        x86os_print_number(trace);x86os_putchar('\\n');return trace ? 98 : 0;
    }
'''
    close = "    if (handle) { int closed = reist_vfs_file_close(handle); if (!result) result = closed; }"
    if source.count(close)!=1: raise ValueError("private stale reuse anchor")
    stale = '''    if(result && handle) {
        int stale=sync_file(handle);
        x86os_puts(stale<0 ? "R342_PRIVATE_STALE_REJECTED\\n" : "R342_PRIVATE_STALE_ACCEPTED\\n");
    }
'''
    candidate=source.replace(anchor,helper+anchor+observe).replace(end,trailer+end).replace(close,stale+close)
    if candidate.replace(helper,"",1).replace(observe,"",1).replace(stale,"",1).replace(trailer,"",1)!=source:
        raise ValueError("private client inverse")
    return candidate


def private_image(reference, evidence, mode):
    original = ROOT / "userspace/programs/storage_service.c"
    generated = evidence / f"storage-{mode}.c"
    generated.write_text(private_source(original.read_text(encoding="utf-8"), mode), encoding="utf-8")
    sources = list(PROGRAMS["STORAGE.PRG"])
    if sources.count(original) != 1: raise ValueError("Storage source registry")
    sources[sources.index(original)] = generated
    program = evidence / f"storage-{mode}.prg"
    old_run = builder.run
    def bounded_run(command, environment=None):
        with (evidence / f"compile-{mode}.log").open("a", encoding="utf-8") as log:
            subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
                check=True, timeout=90, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        builder.run = bounded_run
        builder.build(sources, program, builder.find_zig(),
            include_dirs=[ROOT / "userspace/sdk/include", ROOT / "userspace/storage/include", ROOT],
            runtime_objects=[ROOT / "build/sdk/usr/lib/crt0.o"],
            runtime_libraries=[ROOT / "build/sdk/usr/lib/libreistos.a", ROOT / "build/sdk/usr/lib/libreistc.a"],
            compile_flags=["-fno-inline-functions", "-fno-unroll-loops", "-falign-functions=1", "-ffunction-sections", "-fdata-sections", "-iquote", str(original.parent)],
            dependency_files=[ROOT / "drivers/block/ata_journal.h"],
            cache_directory=ROOT / "build/zig-global-cache")
    finally: builder.run = old_run
    if program.stat().st_size > 224*1024: raise ValueError("private Storage rescue-cache image budget")
    files, sectors, serial = handoff.volume_files(reference)
    if files["libexec/reist/storage.prg"] != (ROOT / "build/programs/STORAGE.PRG").read_bytes():
        raise ValueError("reference Storage mismatch")
    files["libexec/reist/storage.prg"] = program.read_bytes()
    client = ROOT / "userspace/programs/fwritest.c"
    generated_client = evidence / f"fwritest-{mode}.c"
    generated_client.write_text(private_client_source(client.read_text(encoding="utf-8"), exhaust=mode == 6),encoding="utf-8")
    private_client = evidence / f"fwritest-{mode}.prg"
    client_sources = [generated_client if p==client else p for p in PROGRAMS["FWRITEST.PRG"]]
    try:
        builder.run = bounded_run
        builder.build(client_sources, private_client, builder.find_zig(),
            include_dirs=[ROOT / "userspace/sdk/include", ROOT / "userspace/storage/include", ROOT],
            runtime_objects=[ROOT / "build/sdk/usr/lib/crt0.o"],
            runtime_libraries=[ROOT / "build/sdk/usr/lib/libreistos.a",ROOT / "build/sdk/usr/lib/libreistc.a",
                ROOT / "build/sdk/usr/lib/libclang_rt.builtins-i386.a"],
            compile_flags=["-iquote",str(client.parent)],cache_directory=ROOT / "build/zig-global-cache")
    finally: builder.run=old_run
    files["bin/fwritest.prg"] = private_client.read_bytes()
    validate_rescue_sizes({path:len(files[path]) for path in RESCUE_FILES})
    expected = dict(files); files.pop("readme.txt")
    image = evidence / f"private-{mode}.img"
    if image.exists(): raise ValueError("private image already exists")
    shutil.copyfile(reference, image)
    with image.open("r+b") as stream: write_fat32_volume(stream, 8192, sectors, serial, files)
    if handoff.volume_files(image)[0] != expected or kernel_digest(image) != kernel_digest(reference):
        raise ValueError("private image kernel/payload drift")
    return image


class Guest:
    def __init__(self, qemu, image, disk, evidence, name, deadline):
        self.name, self.evidence = name, evidence
        self.deadline = min(deadline, time.monotonic()+180)
        self.continuity = handoff.HostContinuity(); self.continuity.start()
        try: self.process, self.timer = handoff.start_guest(qemu, image, disk)
        except BaseException:
            self.continuity.stop(); raise
        self.chunks, self.transcript = queue.Queue(maxsize=handoff.LIMIT+1), []
        self.finished, self.stopping = threading.Event(), threading.Event()
        self.state, self.diagnostics, self.commands = {"error": None}, [], []
        self.thread = threading.Thread(target=handoff.read_handoff_output,
            args=(self.process, evidence / f"{name}-live.log", self.chunks, self.finished, self.stopping, self.state), daemon=True)
        self.thread.start(); self.prompt = -1

    def text(self):
        smoke.drain(self.chunks, self.transcript)
        return "".join(self.transcript)

    def wait(self, marker, after=-1):
        error, position = handoff.wait_handoff_line(self.process, self.chunks, self.transcript,
            self.finished, marker, self.deadline, self.diagnostics, after=after, continuity=self.continuity)
        if error: raise ValueError(error)
        return position

    def boot(self):
        self.prompt = self.wait(smoke.SHELL_PROMPT, self.wait(smoke.BOOT_MARKER))
        if "REIST OS userspace shell" not in self.text(): raise ValueError("Ring3 shell missing")

    def execute(self, command, required=(), forbidden=(), *, root_after_degraded=False):
        if time.monotonic() >= self.deadline or self.finished.is_set() or self.continuity.check():
            raise ValueError("guest command deadline/observer")
        start = self.prompt
        smoke.inject_ps2_command(self.process, command)
        if root_after_degraded:
            self.wait("R342_PRIVATE_ROOT_WAIT", start)
            degraded = self.wait("REIST_STORAGE SERVICE_DEGRADED", start)
            smoke.qemu_monitor_command(self.process, "sendkey r")
            self.wait("R342_PRIVATE_ROOT_READ_OK", degraded)
        self.prompt = self.wait(smoke.SHELL_PROMPT, start)
        output = self.text()[start+1:self.prompt]
        handoff.validate_handoff_command(output, required, forbidden)
        self.commands.append(command)
        print("FAT32_WRITE_STEP", self.name, command, "PASS", flush=True)
        return output

    def close(self):
        self.stopping.set(); smoke.stop_process(self.process); self.finished.wait(timeout=1)
        self.thread.join(timeout=1); self.continuity.stop()
        raw = self.text()
        (self.evidence / f"{self.name}.log").write_text(raw, encoding="utf-8")
        if self.thread.is_alive(): self.state["error"] = "serial reader did not stop"
        if self.state["error"] or self.continuity.problem or handoff.guard_failure_marker(raw):
            raise ValueError(self.state["error"] or self.continuity.problem or "fatal marker")
        return raw


def object_line_position(text, expected, after=-1):
    position = handoff.handoff_line_position(text, expected, after)
    quarantine = "REIST_STORAGE RESOURCE_QUARANTINED 1"
    stale = ("R342_PRIVATE_STALE_REJECTED", "R342_PRIVATE_STALE_ACCEPTED")
    if position >= 0 or expected not in (quarantine, *stale):
        return position
    # Kernel lifecycle output may interrupt a character-wise FAIL or stale-
    # handle receipt. Reconstruct both REJECTED and ACCEPTED, never an
    # arbitrary embedded marker. Retain raw offsets and the original deadline.
    pattern = re.compile(r"(?:^|\n)([^\r\n]{1,64})(" + re.escape(quarantine) +
        r")\r?\n(?:REIST_STORAGE SERVICE_RETIRED pid=([1-9][0-9]{0,9}) "
        r"generation=([1-9][0-9]{0,9})\r?\n)?([^\r\n]{1,64})\r?\n")
    for match in pattern.finditer(text):
        receipt = match[1] + match[5]
        failure = re.fullmatch(r"FWRITE FAIL stage=[1-7] result=(-[1-9][0-9]{0,9})", receipt)
        position = match.start(2) if expected == quarantine else match.start(1)
        if ((receipt in stale or (failure and int(failure[1]) >= -0x80000000)) and
            (expected == quarantine or expected == receipt) and
            (match[3] is None or (int(match[3]) <= 0x7fffffff and int(match[4]) <= 0xffffffff)) and
            position > after):
            return position
    return -1


def validate_hang_interval(text, start):
    """Boot deliberately faults the probe; the tested operation must not fault."""
    if start < 0 or not text.startswith(smoke.SHELL_PROMPT, start):
        raise ValueError("hang observation boundary missing")
    interval = text[start:]
    if "*** USER PROCESS " in interval or "Exception:" in interval:
        raise ValueError("hang replaced by fault")


def run_case(qemu, image, evidence, mode, deadline):
    name = CASES[mode]
    disk = evidence / f"{name}-fat32.img"
    initial = fixture(disk)
    guest = Guest(qemu, image, disk, evidence, name, deadline)
    started = time.monotonic(); error = None; oracle = DiskOracle(initial)
    raw = ""
    try:
        guest.boot()
        before = guest.prompt
        command = f"fwritest {PATH} --test-data" + ("" if not mode else " pwrite")
        output = guest.execute(command, ("FWRITE OK stage=7 result=0",) if not mode else
            ("print('Hello from REIST JavaScript');", "R342_PRIVATE_ROOT_READ_OK") if mode == 6 else (),
            ("FWRITE FAIL",) if not mode else ("FWRITE OK",), root_after_degraded=mode == 6)
        if not mode:
            for record in plan_records(output): oracle.apply(record)
            if oracle.data_progress != {1:131072,4:4097} or get32(oracle.raw, DATA*512+28) != 513:
                raise ValueError("incomplete normal exercise")
            if private_stats(output)[6] != oracle.flushes: raise ValueError("actual flush count differs from four-barrier plans")
            expected = bytes(oracle.raw)
            guest.execute(f"FWRITEST {PATH} --test-data sync", ("FWRITE OK stage=2 result=0",))
        else:
            if "FWRITE FAIL" not in output: raise ValueError("failed operation receipt missing")
            if (object_line_position(output, "R342_PRIVATE_STALE_REJECTED") < 0 or
                object_line_position(output, "R342_PRIVATE_STALE_ACCEPTED") >= 0):
                raise ValueError("actual old handle reuse did not fail closed")
            # Fixed exercise/fixture: first maximal overwrite is independently
            # determined (offset3,20 separated sectors). A reaped service loses
            # its RAM observer; the exact whole-media oracle is still mandatory.
            oracle.apply([1,3,10237,SIZE,SIZE,0,0,20]+[DATA+1+7*i for i in range(20)])
            if mode in (1,5,6) and "EAX=0x342FA017" not in guest.text(): raise ValueError("actual owner fault missing")
            if mode == 2: validate_hang_interval(guest.text(), before)
            if mode == 3:
                if "EAX=0x342FA019" not in guest.text() or "EAX=0x342FA01A" in guest.text():
                    raise ValueError("expired authority denial witness missing")
            guest.wait("REIST_STORAGE RESOURCE_QUARANTINED 1", before)
            handoff.wait_replacement(guest.process, guest.chunks, guest.transcript, before,
                guest.deadline, guest.continuity, guest.finished)
            guest.execute(f"fwritest {PATH} --test-data sync", (), ("FWRITE OK",))
            if mode == 6:
                # Exhaustion is checked by lifecycle records and sustained denial,
                # not by automatically supplying a new service/repair lease.
                guest.wait("REIST_STORAGE SERVICE_DEGRADED", before)
                if guest.text().count("EAX=0x342FA018") != 3: raise ValueError("three actual recovery cuts required")
                expected = oracle.rollback(active=True)
                # The first target restored before every injected crash is exact.
                sector, undo = oracle.last_undo[-1]
                expected = bytearray(expected); expected[sector*512:(sector+1)*512] = undo
                expected = bytes(expected)
            else:
                for _ in range(12):
                    observed=guest.execute("fwritest --r342-observe")
                    if "R342_PRIVATE_DUMP result=0" in observed and private_stats(observed)[11]&2: break
                else: raise ValueError("successful repair COMMIT witness missing")
                if mode == 5 and "EAX=0x342FA018" not in guest.text(): raise ValueError("actual recovery cut missing")
                expected = bytes(oracle.raw) if mode == 4 else oracle.rollback()
                guest.execute("umount 1", ("ADMIN UMOUNT_OK resource=1",))
                guest.execute("mount 1 fat32 /mnt/hdd1", ("ADMIN MOUNT_OK resource=1 path=/mnt/hdd1",))
                guest.execute(f"fwritest {PATH} --test-data sync", ("FWRITE OK stage=2 result=0",))
        if mode == 6:
            # CAT deliberately requires the exhausted file-object service.
            # The original still-running probe already read the SAME root
            # file after DEGRADED. Now verify continued service denial and
            # shell dispatch from the existing rescue cache. No extra restart.
            identities = handoff.service_records(guest.text())
            guest.execute("cat /htdocs/hello.js", ("cat: cannot open file",))
            if handoff.service_records(guest.text()) != identities:
                raise ValueError("exhausted service restarted during root proof")
        else:
            guest.execute("cat /htdocs/hello.js", ("print('Hello from REIST JavaScript');",))
        if disk.read_bytes() != expected: raise ValueError("exact whole-media oracle mismatch")
        (evidence / f"{name}-expected.img").write_bytes(expected)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as caught: error = str(caught)
    finally:
        try:
            raw = guest.close()
            if mode == 2 and error is None: validate_hang_interval(raw, before)
        except (OSError, ValueError, RuntimeError) as caught: error = error or str(caught)
    report = {"case":name,"passed":error is None,"error":error,"commands":guest.commands,
        "plans":oracle.plans,"expected_normal_flushes":oracle.flushes,
        "host_timer_policy":guest.timer,"host_continuity":guest.continuity.report(),
        "diagnostics":guest.diagnostics,"elapsed_seconds":round(time.monotonic()-started,3),
        "sha256":handoff.transport.file_sha256(disk)}
    (evidence / f"{name}.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("FAT32_WRITE_CASE",name,"PASS" if error is None else "FAIL: "+error,flush=True)
    return report


def archive_closed_private_image(image, *, case_media=False):
    """Lossless archive after run_case has stopped QEMU, never during a case."""
    image = image.resolve()
    pattern = ("(?:" + "|".join(map(re.escape, CASES)) + r")-(?:fat32|expected)\.img"
        if case_media else r"private-[0-6]\.img")
    if (not image.is_relative_to(ALLOWED.resolve()) or image.parent == ALLOWED.resolve() or
        not re.fullmatch(pattern, image.name) or not image.is_file()):
        raise ValueError("closed private image archive target")
    if os.name == "nt":
        before = handoff.transport.file_sha256(image)
        result = subprocess.run(["compact.exe", "/C", "/I", "/Q", str(image)],
            cwd=ROOT, capture_output=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        (image.parent / (image.stem + "-archive.log")).write_bytes(result.stdout + result.stderr)
        result.check_returncode()
        if before != handoff.transport.file_sha256(image):
            raise ValueError("closed archive changed image bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qemu",type=Path,required=True)
    parser.add_argument("--image",type=Path,required=True)
    parser.add_argument("--evidence",type=Path,required=True)
    args = parser.parse_args()
    qemu,image,evidence = args.qemu.resolve(),args.image.resolve(),args.evidence.resolve()
    if not qemu.is_file() or not image.is_file() or evidence.exists() or evidence == ALLOWED.resolve() or not evidence.is_relative_to(ALLOWED.resolve()):
        parser.error("existing qemu/image and fresh r342 evidence child required")
    evidence.mkdir(parents=True); suppress_windows_test_dialogs()
    reference = handoff.transport.file_sha256(image); started = time.monotonic()
    report = {"passed":False,"cases":[],"reference_sha256":reference}
    previous = smoke.exact_line_position,smoke.failure_marker,smoke.monitor_key_commands
    smoke.exact_line_position,smoke.failure_marker,smoke.monitor_key_commands = object_line_position,handoff.guard_failure_marker,object_keys
    try:
        for mode in range(len(CASES)):
            if time.monotonic() >= started+1080: raise ValueError("campaign1080s deadline")
            private = private_image(image,evidence,mode)
            result = run_case(qemu,private,evidence,mode,started+1080)
            report["cases"].append(result)
            archive_closed_private_image(private)
            # Preserve both the observed medium and independent oracle byte
            # for byte, after close/oracle evaluation only. Keeping completed
            # evidence compressed prevents host disk exhaustion in later cases.
            for suffix in ("fat32", "expected"):
                closed = evidence / f"{CASES[mode]}-{suffix}.img"
                if closed.is_file(): archive_closed_private_image(closed, case_media=True)
            if not result["passed"]: break
        report["passed"] = len(report["cases"]) == len(CASES) and all(r["passed"] for r in report["cases"])
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as caught: report["error"] = str(caught)
    finally:
        smoke.exact_line_position,smoke.failure_marker,smoke.monitor_key_commands = previous
        if reference != handoff.transport.file_sha256(image): report.update(passed=False,error="reference modified")
        report["elapsed_seconds"] = round(time.monotonic()-started,3)
        (evidence / "result.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("FAT32_WRITABLE_OBJECTS", "PASS" if report["passed"] else "FAIL",report.get("error",""),flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
