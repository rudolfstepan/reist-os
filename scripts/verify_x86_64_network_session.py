"""Bounded native network-session build and acceptance evidence."""
from pathlib import Path
import argparse, subprocess, time, sys
import verify_x86_64_network_dma as evidence
evidence.EVIDENCE=evidence.ROOT/'build/codex-agent/r83bl-network-session'
evidence.HEAD='de02d6b6'
evidence.PACKAGE='R8.3bl-network-session'
evidence.BUILD='14'
evidence.BASE=evidence.EVIDENCE/'candidate06'
MEDIA='11'

def defaults():
    import ast,re
    from verify_x86_64_service_console import disabled
    v=evidence
    for n,assembly in (('arch/x86_64/proc/task_family.inc',True),('userspace/sdk/lib/x86_64/shell_session.c',False)):
        value=disabled((v.ROOT/n).read_text(encoding='utf-8'),'REIST_NATIVE_NETWORK_SESSION',assembly)
        v.need(value.rstrip()==v.original(n).rstrip(),'exact disabled production '+n)
    def replace(s,a,b=''):
        v.need(s.count(a)==1,'one explicit opt-in addition '+a[:75]);return s.replace(a,b)
    n='scripts/build-x86_64-bootstrap.ps1';s=(v.ROOT/n).read_text(encoding='utf-8')
    for a in ('    [switch]$NativeNetworkSession,\n',
              'if ($NativeNetworkSession) {\n    if ($NativeDisplay -or $NativeInput -or $NativeTerminalService -or $NativeGraphicalSession) {\n        throw \'NativeNetworkSession excludes graphical profiles.\'\n    }\n    $NativeNetworkDMA = [switch]$true\n    $NativeAppFiles = [switch]$true\n}\n',
              '        "X86_64_NATIVE_NETWORK_SESSION=$([int]$NativeNetworkSession.IsPresent)" `\n'):s=replace(s,a)
    v.need(s==v.original(n),'exact disabled Windows build')
    n='Makefile';s=(v.ROOT/n).read_text(encoding='utf-8')
    s,count=re.subn(r'# NativeNetworkSession:.*?# End NativeNetworkSession selector\.\n','',s,flags=re.S);v.need(count==1,'one Make selector')
    s=replace(s,'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_NETWORK_SESSION)),--network-session,)\n')
    s=replace(s,'.PHONY: x86_64-network-media\nX86_64_NETWORK_MEDIA_INPUT ?= build/x86_64\nX86_64_NETWORK_MEDIA_OUTPUT ?= build/codex-agent/native-network-media\nx86_64-network-media:\n\t@$(PYTHON) scripts/build_x86_64_network_media.py --input-directory "$(X86_64_NETWORK_MEDIA_INPUT)" --output-directory "$(X86_64_NETWORK_MEDIA_OUTPUT)" --nasm "$(AS)" --openssl "$(OPENSSL)"\n\n')
    s=replace(s,'ifeq ($(X86_64_NATIVE_NETWORK_SESSION),1)\n\t@$(PYTHON) scripts/build_x86_64_boot_programs.py --compact-input-elf $(X86_64_BOOTSTRAP_ELF) --objcopy $(OBJCOPY) --network-session\nelse ifeq ($(X86_64_NATIVE_INPUT),1)', 'ifeq ($(X86_64_NATIVE_INPUT),1)')
    v.need(s==v.original(n),'exact disabled Make build')
    n='scripts/build_x86_64_boot_programs.py';s=(v.ROOT/n).read_text(encoding='utf-8')
    # Specialize the new selector to false, then compare the complete old AST.
    s=s.replace(',network_session=False', '').replace(',a.network_session','')
    s=replace(s,'    if type(network_session) is not bool or network_session and (not network_dma or not app_files or display or input or terminal_service or graphical_session):raise ValueError("network session requires DMA/application files and excludes GUI")\n')
    s=s.replace('network_dma and not network_session','network_dma')
    s=replace(s,"    if network_session:cc=[*cc,'-DREIST_NATIVE_NETWORK_SESSION=1','-I'+str(attempt)]\n")
    s=replace(s,"    if network_session:\n        from build_x86_64_network_programs import build_roles as network_roles\n        from build_x86_64_graphical_programs import hash_inputs\n        for role in network_roles(attempt,cc,nasm,ld):(attempt/'root'/role.name).write_bytes(role.read_bytes())\n        network_hash_sources,network_hash_flags=hash_inputs(attempt,True)\n")
    s=replace(s,"        if (graphical_session or network_session) and shell_root:\n            role_sources=([ 'userspace/sdk/lib/x86_64/network_session.c',*network_hash_sources] if network_session else ['userspace/sdk/lib/x86_64/graphical_session.c',*graphical_hash_sources])\n            role_hash_flags=network_hash_flags if network_session else graphical_hash_flags\n            for index,source in enumerate(role_sources):",
                "        if graphical_session and shell_root:\n            for index,source in enumerate(['userspace/sdk/lib/x86_64/graphical_session.c',*graphical_hash_sources]):")
    s=s.replace('*role_hash_flags','*graphical_hash_flags')
    s=replace(s,"    if type(network_session) is not bool or network_session and terminal_service:raise ValueError('exclusive network compaction selector')\n    prefixes=('native_pio_','native_terminal_','native_network_') if network_session else ('native_input_', 'native_terminal_') if terminal_service else ('native_input_',)\n    removed={n for n,s in before['symbols'].items() if n.startswith(prefixes) and '.' in n and s['binding']==0}",
                "    removed={n for n,s in before['symbols'].items() if (n.startswith('native_input_') or terminal_service and n.startswith('native_terminal_')) and '.' in n and s['binding']==0}")
    s=s.replace(";p.add_argument('--network-session',action='store_true')",'')
    s=replace(s,"    p.add_argument('--network-session',action='store_true')\n")
    v.need(ast.dump(ast.parse(s))==ast.dump(ast.parse(v.original(n))),'complete disabled program-builder AST')
    # Current package cannot alter any previously accepted immutable artifacts.
    for receipt in ('r83bi-graphical-session/development-build07.json','r83bk-network-fatal/build01.json'):
        old=v.read(v.ROOT/'build/codex-agent'/receipt)
        v.need(all(v.digest(v.ROOT/n)==sha for n,sha in old['artifacts'].items()),'accepted artifact retention '+receipt)
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=v.ROOT,timeout=120,check=True)
    print('NETWORK_SESSION_DEFAULTS_OK')

def qualification_tools():
    import shutil
    from verify_x86_64_graphical_session import build_tools
    from run_qemu_x86_64_boot import resolve_qemu
    v=evidence;result=build_tools()
    for name,path in (('qemu',resolve_qemu(None)),('gdb',shutil.which('gdb'))):
        v.need(path is not None,'qualification tool '+name);path=Path(path).resolve()
        result[name]=dict(path=str(path),sha256=v.digest(path))
    return result

def freeze():
    v=evidence;v.need(not v.BASE.exists() and v.git('rev-parse','--short=8','HEAD')==v.HEAD,'fresh candidate/base')
    p=v.package_row();paths=v.changed();v.need(set(paths)<=set(p['allowed_files']) and not v.git('diff','--cached','--name-only'),'unstaged frozen scope')
    subprocess.run(['git','diff','--check'],cwd=v.ROOT,check=True)
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];v.need(len(commands)==5,'five frozen gates')
    v.save(v.BASE/'frozen.json',dict(head=v.git('rev-parse','HEAD'),package=p,changed=paths,sources=v.sources(),
        tools=qualification_tools(),commands=commands,limits=[600,180,180,2700,600],image=v.link(v.image()),media=v.link(v.EVIDENCE/('media'+MEDIA)/'network-media.json')))

def binding():
    v=evidence;f=v.read(v.BASE/'frozen.json')
    v.need(f['head']==v.git('rev-parse','HEAD') and f['package']==v.package_row() and f['changed']==v.changed() and
           f['sources']==v.sources() and f['tools']==qualification_tools(),'immutable candidate');return f

def gates():
    # Reuse the deterministic exactly-once/stop-first-failure controller.
    evidence.binding=binding;evidence.gates()

def package():
    import check_x86_64_network_media as consumer
    v=evidence;f=binding();image=v.image();receipt=v.read(v.EVIDENCE/('media'+MEDIA+'.json'))
    v.need(receipt['passed'] and receipt['elapsed']<=180,'bounded signed package')
    v.need(receipt['index']==f['media'] and receipt['index']==v.link(v.EVIDENCE/('media'+MEDIA)/'network-media.json'),'exact signed index')
    consumer.verify(v.EVIDENCE/('media'+MEDIA))
    v.save(v.BASE/'package.json',dict(passed=True,image=v.link(image),media=f['media']))

def runtime():
    import run_qemu_x86_64_network_session as guest
    v=evidence;binding();image=v.image();rows=[]
    for spec in guest.CASES:
        binding();folder=v.BASE/'guests'/spec[0]
        row=guest.diagnostic(image,folder,spec[1],spec[2]);row['proof']=guest.review(image,folder,spec)
        rows.append(row);v.save(v.BASE/(spec[0]+'.json'),row);print('NETWORK_SESSION_CASE_OK',spec[0],flush=True)
    v.need(sum(r['elapsed'] for r in rows)<=2520,'aggregate frozen guest bound')
    v.save(v.BASE/'matrix.json',dict(passed=True,cases=rows))

def review():
    import run_qemu_x86_64_network_session as guest
    v=evidence;binding();image=v.image();matrix=v.read(v.BASE/'matrix.json')
    v.need(matrix['passed'] and len(matrix['cases'])==14,'fourteen fresh cases')
    for row,spec in zip(matrix['cases'],guest.CASES):v.need(guest.review(image,v.BASE/'guests'/spec[0],spec)==row['proof'],'independent raw replay')
    v.need(set(v.changed())<=set(v.package_row()['allowed_files']) and not v.git('diff','--cached','--name-only'),'final scope')
    subprocess.run(['git','diff','--check'],cwd=v.ROOT,check=True)
    v.save(v.BASE/'review.json',dict(passed=True,raw={p.relative_to(v.ROOT).as_posix():v.digest(p) for p in (v.BASE/'guests').rglob('*') if p.is_file()}))

def development_build():
    v=evidence;folder=v.EVIDENCE/('build'+v.BUILD);receipt=v.EVIDENCE/('build'+v.BUILD+'.json')
    v.need(not folder.exists() and not receipt.exists(),'fresh reserved build')
    state=v.build_sources();tool=v.tools()
    cmd=[tool['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
         '-NativeNetworkSession','-OutputDirectory',folder.relative_to(v.ROOT).as_posix()]
    log=v.EVIDENCE/('build'+v.BUILD+'.log')
    row=dict(passed=False,command=cmd,sources=state,tools=tool,limit=300)
    v.save(v.EVIDENCE/('build'+v.BUILD+'-started.json'),row);start=time.monotonic()
    try:
        with log.open('xb') as out:
            p=subprocess.run(cmd,cwd=v.ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=300)
        v.need(p.returncode==0,'build failed: '+log.read_text(errors='replace')[-2200:])
        v.need(state==v.build_sources() and tool==v.tools(),'unchanged build inputs')
        row['artifacts']={p.relative_to(v.ROOT).as_posix():v.digest(p) for p in folder.rglob('*')
            if p.is_file() and not any('cache' in a for a in p.parts)
            and p.suffix in ('.elf','.prg','.bin','.json','.inc','.map','.o')}
        row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(elapsed=time.monotonic()-start,log=v.link(log));v.save(receipt,row)
    print('NETWORK_SESSION_BUILD_OK',row['elapsed'])

def development_media():
    import check_x86_64_network_media as consumer
    from verify_x86_64_graphical_session import build_tools as media_tools
    v=evidence;image=v.image();folder=v.EVIDENCE/('media'+MEDIA);receipt=v.EVIDENCE/('media'+MEDIA+'.json')
    v.need(not folder.exists() and not receipt.exists(),'fresh reserved signed media')
    tool=media_tools();state=v.sources()
    command=[sys.executable,'scripts/build_x86_64_network_media.py','--input-directory',str(image.parent),
             '--output-directory',str(folder),'--nasm',tool['nasm']['path'],'--openssl',tool['openssl']['path']]
    row=dict(passed=False,command=command,sources=state,tools=tool,limit=180,bios_assemblies=3)
    v.save(v.EVIDENCE/('media'+MEDIA+'-started.json'),row);start=time.monotonic();log=v.EVIDENCE/('media'+MEDIA+'.log')
    try:
        with log.open('xb') as out:
            p=subprocess.run(command,cwd=v.ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=180)
        v.need(p.returncode==0,'media failed: '+log.read_text(errors='replace')[-2400:])
        v.need(state==v.sources() and tool==media_tools(),'unchanged media inputs')
        row['package']=str(consumer.verify(folder));row['index']=v.link(folder/'network-media.json');row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(elapsed=time.monotonic()-start,log=v.link(log));v.save(receipt,row)
    print('NETWORK_SESSION_MEDIA_OK',row['elapsed'])

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('development-build','development-media','freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    if a.development_build:development_build()
    elif a.development_media:development_media()
    elif a.freeze:freeze()
    elif a.gates:gates()
    elif a.defaults:defaults()
    elif a.package:package()
    elif a.runtime:runtime()
    elif a.review:review()
