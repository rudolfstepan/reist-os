"""Frozen fatal-boundary qualification, sharing the accepted bounded runner."""
import argparse,subprocess,sys
from pathlib import Path
import verify_x86_64_network_dma as v
v.EVIDENCE=v.ROOT/'build/codex-agent/r83bk-network-fatal'
v.BASE=v.EVIDENCE/'candidate03';v.HEAD='b7ee5e7a';v.PACKAGE='R8.3bk-network-fatal';v.BUILD='01'

def defaults():
    from verify_x86_64_service_console import disabled
    n='Makefile';s=(v.ROOT/n).read_text(encoding='utf-8')
    addition=' $(X86_64_NETWORK_FLAGS) arch/x86_64/cpu/exceptions.asm'
    v.need(s.count(addition)==1,'one explicit exception selector')
    v.need(s.replace(addition,' arch/x86_64/cpu/exceptions.asm')==v.original(n),'exact old Makefile')
    n='arch/x86_64/cpu/exceptions.asm'
    v.need(disabled((v.ROOT/n).read_text(encoding='utf-8'),'REIST_NATIVE_NETWORK_DMA',True)==v.original(n),'exact non-network exception path')
    n='arch/x86_64/devices/network_domain.inc';s=(v.ROOT/n).read_text(encoding='utf-8');old=v.original(n)
    v.need(s.split('native_network_emergency64:\n')[0]==old.split('native_network_emergency64:\n')[0],'all operational mediation unchanged')
    v.need(s.split('section .bss\n')[1].replace('native_network_fatal_receipt: resq 8\n','')==old.split('section .bss\n')[1],'one fixed receipt only')
    n='arch/x86_64/devices/network_dma.c';s=(v.ROOT/n).read_text(encoding='utf-8');old=v.original(n)
    a=old.index('    if(c->mode==4)');b=old.index('    if(c->mode==0)',a);old=old[:a]+old[b:]
    a=old.index('    if(c->result==-84)');b=old.index('    return 1;',a)
    old=old[:a]+'    /* Assembly immediately enters the metadata-independent fatal fence. */\n    if(c->result==-84)return 0;\n'+old[b:]
    v.need(s==old,'only obsolete C emergency removed')
    accepted=v.read(v.ROOT/'build/codex-agent/r83bj-network-dma/build03.json')
    v.need(all(v.digest(v.ROOT/n)==sha for n,sha in accepted['artifacts'].items()),'accepted BJ artifacts intact')
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=v.ROOT,timeout=120,check=True)
    print('NETWORK_FATAL_DEFAULTS_OK')

def package():
    v.binding();image=v.image()
    import run_qemu_x86_64_program_memory as w
    s=w.transport.symbols(image)
    v.need(s['native_network_fatal_receipt']%8==0 and s['native_network_fatal_receipt']-s['native_network_call']==1656,'unchanged scrub extent')
    dump=subprocess.check_output(['objdump','-d','--start-address='+hex(s['exception_fatal']-0xffffffff80000000),'--stop-address='+hex(s['exception_fatal']-0xffffffff80000000+5),str(image)],text=True,timeout=10)
    v.need('native_network_emergency64' in dump,'actual linked exception fence before diagnostics')
    v.save(v.BASE/'package.json',dict(passed=True,image=v.link(image)))

def runtime():
    import run_qemu_x86_64_network_dma as ordinary
    import run_qemu_x86_64_network_fatal as fatal
    rows=[]
    for spec in ordinary.CASES:
        v.binding();folder=v.BASE/'guests'/spec[0];row=fatal.ordinary_run(v.image(),folder,spec);row['proof']=fatal.ordinary_review(v.image(),folder,spec)
        rows.append(row);v.save(v.BASE/(spec[0]+'.json'),row);print('NETWORK_NORMAL_OK',spec[0],flush=True)
    for kind in fatal.CASES:
        v.binding();folder=v.BASE/'guests'/kind;row=fatal.run(v.image(),folder,kind);row['proof']=fatal.review(v.image(),folder,kind)
        rows.append(row);v.save(v.BASE/(kind+'.json'),row);print('NETWORK_FATAL_OK',kind,flush=True)
    v.need(sum(r['elapsed'] for r in rows)<=495,'aggregate guest deadline');v.save(v.BASE/'matrix.json',dict(passed=True,cases=rows))

def review():
    import run_qemu_x86_64_network_dma as ordinary
    import run_qemu_x86_64_network_fatal as fatal
    v.binding();matrix=v.read(v.BASE/'matrix.json');v.need(matrix['passed'] and len(matrix['cases'])==11,'all eleven cases')
    for row,spec in zip(matrix['cases'][:8],ordinary.CASES):v.need(fatal.ordinary_review(v.image(),v.BASE/'guests'/spec[0],spec)==row['proof'],'normal raw replay')
    for row,kind in zip(matrix['cases'][8:],fatal.CASES):v.need(fatal.review(v.image(),v.BASE/'guests'/kind,kind)==row['proof'],'fatal raw replay')
    v.need(set(v.changed())<=set(v.package_row()['allowed_files']) and not v.git('diff','--cached','--name-only'),'scope')
    subprocess.run(['git','diff','--check'],cwd=v.ROOT,check=True)
    v.save(v.BASE/'review.json',dict(passed=True,raw={p.relative_to(v.ROOT).as_posix():v.digest(p) for p in (v.BASE/'guests').rglob('*') if p.is_file()}))

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('development-build','freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    if a.development_build:v.development_build()
    elif a.freeze:v.freeze()
    elif a.gates:v.gates()
    elif a.defaults:defaults()
    elif a.package:package()
    elif a.runtime:runtime()
    elif a.review:review()
