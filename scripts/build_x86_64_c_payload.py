"""Validate the private v2 ELF64 C payload before emitting bootstrap sections.

This is a bounded build tool, never a runtime kernel executable parser.
"""
from pathlib import Path
import argparse, hashlib, json, os, struct, uuid
VERSION=2
ROOT=Path(__file__).resolve().parents[1]
HIGH=0xffffffff80000000
# address, capacity, section flags, section type, program flags
LAYOUT={'.text':(HIGH+0x185000,65536,6,1,5),
        '.rodata':(HIGH+0x195000,32768,2,1,4),
        '.data':(HIGH+0x19d000,16384,3,1,6),
        '.bss':(HIGH+0x1a1000,262144,3,8,6)}
BINDINGS={'x86_64_c_core_entry':HIGH+0x185000,
          'x86_64_c_data_state':HIGH+0x19d000,'x86_64_c_bss_state':HIGH+0x1a1000,
          'x86_64_c_serial_write64':HIGH+0x184000,'x86_64_c_process_shell64':HIGH+0x184100,
          'x86_64_c_process_run64':HIGH+0x184200,'x86_64_c_handoff':HIGH+0x1ff000,
          'x86_64_c_control_handoff':HIGH+0x1ff080}
OUTPUTS=('bootstrap_core_text.bin','bootstrap_core_rodata.bin','bootstrap_core_data.bin',
         'bootstrap_core_layout.inc','bootstrap_core_layout.json')
CALL_EXPORTS={'reist_native_ipc':'C_NATIVE_IPC_ENTRY'}


def require(ok,message):
    if not ok:raise ValueError(message)


def read_bounded(path):
    with Path(path).open('rb') as stream:data=stream.read(1048577)
    require(64<=len(data)<=1048576,'ELF file capacity')
    return data


def elf(data,bits):
    require(64<=len(data)<=1048576,'ELF file capacity')
    require(data[:7]==b'\x7fELF'+bytes((2 if bits==64 else 1,1,1)),'ELF identification')
    require(data[7] in (0,3) and not any(data[8:16]),'ELF ABI/padding')
    fmt='<HHIQQQIHHHHHH' if bits==64 else '<HHIIIIIHHHHHH'
    kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=struct.unpack_from(fmt,data,16)
    require((kind,machine,version,flags,ehsize)==(2,62 if bits==64 else 3,1,0,64 if bits==64 else 52),'ELF executable header')
    require(1<=phnum<=32 and phsize==(56 if bits==64 else 32),'ELF program table capacity')
    require(1<=shnum<=128 and shsize==(64 if bits==64 else 40) and 0<shstr<shnum,'ELF section table capacity')
    def span(off,size):
        require(0<=off<=len(data) and 0<=size<=len(data)-off,'ELF file range')
        return data[off:off+size]
    span(phoff,phnum*phsize);span(shoff,shnum*shsize)
    occupied=[(0,ehsize),(phoff,phoff+phnum*phsize),(shoff,shoff+shnum*shsize)]
    raw=[struct.unpack_from('<IIQQQQIIQQ' if bits==64 else '<IIIIIIIIII',data,shoff+i*shsize) for i in range(shnum)]
    require(not any(raw[0]),'ELF null section')
    require(raw[shstr][1]==3,'ELF section string table')
    names=span(raw[shstr][4],raw[shstr][5])
    def string(table,offset):
        require(0<=offset<len(table),'ELF string offset')
        end=table.find(b'\0',offset,min(offset+256,len(table)))
        require(end>=offset,'ELF string capacity/termination')
        return table[offset:end].decode('ascii')
    sections={};symbols={};symtabs=0
    for i,(name,typ,flags,addr,off,size,link,info,align,entsize) in enumerate(raw[1:],1):
        name=string(names,name)
        require(name and name not in sections,'ELF duplicate/empty section')
        require(size<=1048576 and (align==0 or align&(align-1)==0),'ELF section size/alignment')
        require(addr+size<=1<<bits,'ELF section address overflow')
        content=b'' if typ==8 else span(off,size)
        if typ!=8 and size:occupied.append((off,off+size))
        require(not(flags&1 and flags&4),'ELF writable executable section')
        require(not flags&0x400,'ELF TLS section')
        require(not(typ in (4,9,6,11) and size),'ELF relocation/dynamic state')
        require(not any(name.startswith(p) for p in ('.init_array','.fini_array','.ctors','.dtors','.eh_frame','.gcc_except_table','.tdata','.tbss','.tls')),'ELF forbidden runtime section')
        sections[name]=dict(index=i,type=typ,flags=flags,address=addr,offset=off,size=size,align=align,data=content)
        if typ==2:
            symtabs+=1
            require(entsize==(24 if bits==64 else 16) and size%entsize==0 and size//entsize<=4096,'ELF symbol capacity')
            require(0<link<shnum and raw[link][1]==3,'ELF symbol strings')
            strings=span(raw[link][4],raw[link][5])
            for j in range(size//entsize):
                if bits==64:n,t,other,index,value,length=struct.unpack_from('<IBBHQQ',content,j*entsize)
                else:n,value,length,t,other,index=struct.unpack_from('<IIIBBH',content,j*entsize)
                if j==0:
                    require((n,t,other,index,value,length)==(0,0,0,0,0,0),'ELF null symbol');continue
                require(index!=0,'ELF undefined symbol')
                require(index<shnum or index==0xfff1,'ELF symbol section')
                name=string(strings,n)
                if name:
                    # Local labels may repeat; externally bound names may not.
                    if name in BINDINGS or name in CALL_EXPORTS:require(name not in symbols,'ELF duplicate binding')
                    symbols[name]=dict(value=value,size=length,index=index,type=t&15,binding=t>>4,visibility=other)
    require(symtabs==1,'ELF exact symbol table')
    occupied.sort()
    require(all(a[1]<=b[0] for a,b in zip(occupied,occupied[1:])),'ELF file section/table overlap')
    programs=[]
    for i in range(phnum):
        if bits==64:typ,flags,off,addr,physical,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',data,phoff+i*phsize)
        else:typ,off,addr,physical,filesz,memsz,flags,align=struct.unpack_from('<IIIIIIII',data,phoff+i*phsize)
        require(filesz<=memsz and addr+memsz<=1<<bits,'ELF segment overflow')
        span(off,filesz)
        require(not(flags&1 and flags&2),'ELF writable executable PT_LOAD')
        require(align in (0,1) or align&(align-1)==0,'ELF segment alignment')
        if typ==1:
            require(align>=4096 and off%align==addr%align,'ELF load alignment')
            programs.append(dict(flags=flags,offset=off,address=addr,physical=physical,filesz=filesz,size=memsz))
        else:require(typ==0x6474e551 and flags==6 and filesz==memsz==0,'ELF unsupported program header')
    return dict(entry=entry,sections=sections,symbols=symbols,programs=programs)


def validate(data):
    parsed=elf(data,64);sections=parsed['sections'];symbols=parsed['symbols']
    require(parsed['entry']==BINDINGS['x86_64_c_core_entry'],'C entry binding')
    allocated={n for n,s in sections.items() if s['flags']&2}
    require(allocated==set(LAYOUT),'C allocated section set')
    require(len(parsed['programs'])==4,'C exact load segments')
    occupied=[]
    for name,(addr,cap,flags,typ,pflags) in LAYOUT.items():
        s=sections[name]
        require(s['address']==addr and s['type']==typ and s['flags']==flags,'C section address/type/permissions')
        require((32 if name in ('.data','.bss') else 1)<=s['size']<=cap,'C section capacity')
        require(1<=s['align']<=4096 and addr%s['align']==0,'C section alignment')
        matches=[p for p in parsed['programs'] if p['address']==addr]
        require(len(matches)==1,'C segment binding')
        p=matches[0]
        require(p['physical']==addr and p['flags']==pflags and p['size']==s['size'] and
                p['filesz']==(0 if typ==8 else s['size']) and p['offset']==s['offset'],'C segment content/permissions')
        if typ!=8:
            require(s['offset']>=64,'C section overlaps ELF header')
            occupied.append((s['offset'],s['offset']+s['size']))
    occupied.sort()
    require(all(a[1]<=b[0] for a,b in zip(occupied,occupied[1:])),'C file section overlap')
    for name,address in BINDINGS.items():
        s=symbols.get(name)
        require(s is not None and s['value']==address and s['binding']==1 and s['visibility']==0,'C symbol binding '+name)
        section='.text' if name=='x86_64_c_core_entry' else '.data' if name=='x86_64_c_data_state' else '.bss' if name=='x86_64_c_bss_state' else None
        require(s['index']==(sections[section]['index'] if section else 0xfff1),'C binding section '+name)
        if section in ('.data','.bss'):require(s['size']==32 and s['type']==1,'C boot state object')
        if section=='.text':require(s['type']==2 and 0<s['size']<=sections[section]['size'],'C function entry')
    for name in CALL_EXPORTS:
        if name not in symbols:continue
        s=symbols[name];t=sections['.text']
        require(s['binding']==1 and s['visibility']==0 and s['type']==2 and
                s['index']==t['index'] and s['size']>0 and t['address']<=s['value'] and
                s['value']+s['size']<=t['address']+t['size'],'C call export '+name)
    return parsed


def outputs(data):
    p=validate(data);s=p['sections']
    metadata=dict(version=VERSION,sha256=hashlib.sha256(data).hexdigest(),
                  sections={n:{k:v for k,v in v.items() if k!='data'} for n,v in s.items() if n in LAYOUT},
                  bindings=BINDINGS)
    result={f'bootstrap_core_{n[1:]}.bin':s[n]['data'] for n in ('.text','.rodata','.data')}
    result['bootstrap_core_layout.inc']=(f'; Generated from validated ELF64, private layout v{VERSION}.\n'
        f'%define C_CORE_LAYOUT_VERSION {VERSION}\n%define C_CORE_BSS_BYTES {s[".bss"]["size"]}\n'+
        ''.join(f'%define {define} {p["symbols"].get(name,{}).get("value",0):#x}\n'
                for name,define in CALL_EXPORTS.items())).encode('ascii')
    result['bootstrap_core_layout.json']=(json.dumps(metadata,indent=2,sort_keys=True)+'\n').encode('ascii')
    return result


def verify_outer(inner,outer):
    p=validate(inner);o=elf(outer,32)
    allocated={n:s for n,s in o['sections'].items() if s['flags']&2}
    expected={'.multiboot','.text','.rodata','.data','.bss','.c_core_bridge','.c_core_handoff'}|{'.c_core_'+n[1:] for n in LAYOUT}
    require(set(allocated)==expected,'outer allocated section set')
    require(o['entry']==o['symbols'].get('x86_64_bootstrap_start',{}).get('value') and
            allocated['.text']['address']<=o['entry']<allocated['.text']['address']+allocated['.text']['size'],'outer entry binding')
    segments=sorted(o['programs'],key=lambda p:p['address'])
    require(all(0x100000<=p['address']==p['physical'] and p['address']+p['size']<=0x200000 for p in segments),'outer load range')
    require(all(a['address']+a['size']<=b['address'] for a,b in zip(segments,segments[1:])),'outer load overlap')
    for name,s in allocated.items():
        require(s['size']>0 and s['type'] in (1,8) and s['flags'] in (2,3,6),'outer allocated section contract')
        matches=[p for p in segments if p['address']<=s['address'] and s['address']+s['size']<=p['address']+p['size']]
        require(len(matches)==1,'outer section load binding')
        segment=matches[0];delta=s['address']-segment['address']
        require(segment['flags']==(5 if s['flags']==6 else 6 if s['flags']==3 else 4),'outer section/load permissions')
        if s['type']==1:require(s['offset']==segment['offset']+delta and delta+s['size']<=segment['filesz'],'outer loaded bytes')
        else:require(delta>=segment['filesz'],'outer BSS file alias')
    ordered=sorted(allocated.values(),key=lambda s:s['address'])
    require(all(a['address']+a['size']<=b['address'] for a,b in zip(ordered,ordered[1:])),'outer section overlap')
    bridge=allocated['.c_core_bridge']
    require(bridge['address']==0x184000 and 0x200<bridge['size']<=4096 and bridge['flags']==6 and bridge['type']==1,'outer bridge layout')
    for name in LAYOUT:
        s=p['sections'][name];other=o['sections'].get('.c_core_'+name[1:])
        require(other is not None,'outer C section missing')
        require((other['address'],other['size'],other['flags'],other['type'],other['data'])==
                (s['address']-HIGH,s['size'],s['flags'],s['type'],s['data']),'outer C payload mismatch')
    for name,address in BINDINGS.items():
        s=o['symbols'].get(name)
        section='.c_core_text' if name=='x86_64_c_core_entry' else '.c_core_data' if name=='x86_64_c_data_state' else '.c_core_bss' if name=='x86_64_c_bss_state' else '.c_core_handoff' if 'handoff' in name else '.c_core_bridge'
        require(s is not None and s['value']==address-HIGH and s['binding']==1 and s['visibility']==0 and
                s['index']==allocated[section]['index'],'outer symbol binding '+name)
    handoff=o['sections'].get('.c_core_handoff')
    require(handoff is not None and (handoff['address'],handoff['size'],handoff['flags'],handoff['type'])==
            (0x1ff000,192,3,8),'outer handoff layout')


def publish(data,directory):
    # Validate the entire input and all bytes before creating any output.
    result=outputs(data);directory=Path(directory).resolve()
    require(directory.is_relative_to(ROOT/'build'),'C payload output outside build')
    directory.mkdir(parents=True,exist_ok=True)
    for name,content in result.items():
        target=directory/name
        require(not target.is_symlink(),'C payload output symlink')
    for name,content in result.items():
        temporary=directory/('.c-payload-'+uuid.uuid4().hex)
        owned=False
        try:
            # Ordinary exclusive create inherits destination ACLs on Windows;
            # mkstemp would publish a private sandbox-owner-only artifact.
            with temporary.open('xb') as stream:
                owned=True;stream.write(content);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,directory/name)
        finally:
            if owned and temporary.exists():temporary.unlink()


def main():
    a=argparse.ArgumentParser();a.add_argument('--elf',type=Path,required=True)
    mode=a.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output-directory',type=Path);mode.add_argument('--verify-outer',type=Path)
    args=a.parse_args()
    try:
        data=read_bounded(args.elf)
        if args.verify_outer:verify_outer(data,read_bounded(args.verify_outer))
        else:publish(data,args.output_directory)
        print('X86_64_C_PAYLOAD_LAYOUT_OK version=2');return 0
    except (OSError,ValueError,struct.error) as exc:
        print('X86_64_C_PAYLOAD_LAYOUT_FAIL '+str(exc));return 1


if __name__=='__main__':raise SystemExit(main())
