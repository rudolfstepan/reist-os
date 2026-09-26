"""Bounded development capture of actual BIOS VGA cells and PS/2 shell input.

This healthy diagnostic is not the crash/hang/final package qualification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import socket
import struct
import subprocess
import time
import uuid
import os
import threading
import shutil
import re
import check_x86_64_vga_console_media as check
import run_qemu_x86_64_boot as boot
import run_qemu_x86_64_shell_boot_media as bios
from run_qemu_x86_64_input import QMP as InputQMP
from run_x86_64_display import data_fixture

ROOT=check.ROOT


def cursor_pixels(path,row,column):
    raw=Path(path).read_bytes()
    header=b'P6\n720 400\n255\n'
    check.need(raw.startswith(header) and len(raw)==len(header)+720*400*3,
               'complete mode03 PPM pixels')
    check.need(0<=row<24 and 0<=column<80,'cursor pixel bounds')
    pixels=raw[len(header):]
    # BIOS mode03 uses9x16 cells. A blank prompt cell must contain the
    # hardware underline; text RAM alone cannot establish this result.
    return any(sum(pixels[((row*16+y)*720+column*9+x)*3:((row*16+y)*720+column*9+x)*3+3]!=b'\0\0\0'
                   for x in range(9))>=8 for y in range(13,16))


def console_text(raw):
    check.need(type(raw) is bytes and len(raw)<=262144,'bounded serial text')
    def remove_record(match):
        record=bytes.fromhex(match[1].decode('ascii'))
        slot,generation,_,reason,_,_=struct.unpack('<4I2Q',record)
        check.need(slot<=7 and 0<generation<0x80000000 and 1<=reason<=4,'valid complete reap record')
        return b''
    return re.sub(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})\r\n',remove_record,raw)


class QMP(InputQMP):
    def registers(self):
        # Fixed read-only HMP request; no arbitrary monitor command interface.
        self.seq+=1
        check.need(self.seq<=256 and time.monotonic()<self.end,'register read budget')
        self.sock.sendall((json.dumps({'execute':'human-monitor-command',
            'arguments':{'command-line':'info registers'},'id':self.seq})+'\n').encode())
        for _ in range(32):
            reply=self.read()
            if 'event' in reply:continue
            check.need(reply.get('id')==self.seq and type(reply.get('return')) is str,
                       'register response')
            return reply['return']
        raise ValueError('register event bound')


def fault_witness(image):
    signature=struct.pack('<4Q',0x31414756434a5253,1,0,0)
    check.need(image.count(signature)==1,'unique supervisor fault witness')
    offset=image.index(signature)
    phoff=struct.unpack_from('<Q',image,32)[0]
    count=struct.unpack_from('<H',image,56)[0]
    check.need(1<=count<=8,'root ELF program count')
    for index in range(count):
        kind,rights,start,va,_,filesz,_,_=struct.unpack_from('<II6Q',image,phoff+56*index)
        if kind==1 and rights==6 and start<=offset and offset+32<=start+filesz:
            return va+offset-start
    raise ValueError('fault witness must be in the root writable image')


def fault_observer(folder,port,symbols,image,mode):
    check.need(mode in (1,2),'private fault mode')
    witness=fault_witness(image);base=0xffffffff80000000
    data=dict(port=port,witness=witness,mode=mode,
              breakpoint=base+symbols['process_run_syscall64.pid'],
              slot=base+symbols['scheduler_current_slot'],tick=base+symbols['scheduler_last_tick'],
              proof=str(folder/'fault-injection.json'))
    code='set pagination off\nset confirm off\nset architecture i386:x86-64\npython\n'
    code+='import gdb,json,struct\ncfg='+repr(data)+'\n'
    code+='''inferior=gdb.selected_inferior()
def read(address,size):return bytes(inferior.read_memory(address,size))
class Inject(gdb.Breakpoint):
    hits=0
    done=False
    def stop(self):
        self.hits+=1
        if self.hits>64:raise RuntimeError('fault breakpoint hit limit')
        if struct.unpack('<I',read(cfg['slot'],4))[0]!=0:return False
        try:before=read(cfg['witness'],32)
        except gdb.MemoryError:return False
        if before!=struct.pack('<4Q',0x31414756434a5253,1,0,0):return False
        inferior.write_memory(cfg['witness']+16,struct.pack('<Q',cfg['mode']))
        after=read(cfg['witness'],32)
        assert after==struct.pack('<4Q',0x31414756434a5253,1,cfg['mode'],0)
        record=dict(cfg,before=before.hex(),after=after.hex(),hits=self.hits,
                    tick=struct.unpack('<Q',read(cfg['tick'],8))[0])
        with open(cfg['proof'],'x') as out:json.dump(record,out)
        self.done=True
        return True
gdb.execute('target remote 127.0.0.1:'+str(cfg['port']))
bp=Inject('*'+hex(cfg['breakpoint']),type=gdb.BP_HARDWARE_BREAKPOINT)
gdb.execute('continue')
assert bp.done,'fault rendezvous missing'
bp.delete()
gdb.execute('detach')
end
quit
'''
    script=folder/'fault.gdb';script.write_text(code)
    log=(folder/'fault-observer.log').open('wb')
    process=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
                             cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return process,log


def early_observer(folder,port,symbols):
    base=0xffffffff80000000
    data=dict(port=port,breakpoint=base+symbols['x86_64_nx_resume'],
              target=base+symbols['physical_memory_state_error'],proof=str(folder/'early-injection.json'))
    code='set pagination off\nset confirm off\nset architecture i386:x86-64\npython\n'
    code+='import gdb,json\ncfg='+repr(data)+'\n'
    code+='gdb.execute("target remote 127.0.0.1:"+str(cfg["port"]))\n'
    code+='bp=gdb.Breakpoint("*"+hex(cfg["breakpoint"]),type=gdb.BP_HARDWARE_BREAKPOINT)\n'
    code+='gdb.execute("continue")\nbefore=int(gdb.parse_and_eval("$rip"))\nassert before==cfg["breakpoint"]\n'
    code+='gdb.execute("set $rip="+hex(cfg["target"]))\nafter=int(gdb.parse_and_eval("$rip"))\nassert after==cfg["target"]\n'
    code+='with open(cfg["proof"],"x") as out:json.dump(dict(cfg,before=before,after=after),out)\n'
    code+='bp.delete()\ngdb.execute("detach")\nend\nquit\n'
    script=folder/'early.gdb';script.write_text(code)
    log=(folder/'early-observer.log').open('wb')
    process=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
                             cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return process,log


def diagnostic(directory,folder,case='healthy'):
    check.need(case in ('healthy','crash','hang','early'),'case')
    package=check.verify(Path(directory))
    folder=Path(folder).absolute()
    check.need(folder==folder.resolve() and folder.is_relative_to(ROOT/'build/codex-agent')
               and not folder.exists(),'fresh capture scope')
    folder.mkdir(parents=True)
    start=time.monotonic();end=start+90
    result=dict(passed=False,qualification=False,limit=90,package=str(package),case=case)
    vm=qmp=medium=fixture=errors=debugger=debuglog=reader=None
    reader_errors=[]
    symbols={n:s['value'] for n,s in check.payload.elf((package/check.KERNEL).read_bytes(),32)['symbols'].items()}
    result['kernel_sha256']=hashlib.sha256((package/check.KERNEL).read_bytes()).hexdigest()
    def serial():
        check.need(not reader_errors,'serial reader '+str(reader_errors))
        path=folder/'serial.log'
        if not path.exists():return b''
        check.need(path.stat().st_size<=262144,'serial byte bound')
        return path.read_bytes()
    def snapshot(label):
        out=folder/label;out.mkdir()
        qmp.call('stop',{})
        check.need(not qmp.call('query-status',{})['running'],'paused snapshot')
        registers=qmp.registers()
        (out/'registers.txt').write_text(registers)
        import re
        stack=re.search(r'RSP=([0-9a-fA-F]{16})',registers)
        if stack:
            address=int(stack[1],16)-0xffffffff80000000
            if 0x100000<=address<0x4000000-512:
                qmp.call('pmemsave',dict(val=address,size=512,filename=str(out/'stack.bin')))
        for name,address,size in (('cells',0xb8000,4000),('bios',0x400,256),
                                   ('vga',symbols['native_vga_state'],2272),
                                   ('input',symbols['native_input_state'],128),
                                   ('tasks',symbols['scheduler_tasks'],8192),
                                   ('profiles',symbols['family_profiles'],256),
                                   ('family',symbols['family_records'],512),
                                   ('budgets',symbols['scheduler_cpu_budgets'],256),
                                   ('windows',symbols['scheduler_cpu_windows'],256)):
            qmp.call('pmemsave',dict(val=address,size=size,filename=str(out/(name+'.bin'))))
            check.need((out/(name+'.bin')).stat().st_size==size,'complete '+name)
        tasks=(out/'tasks.bin').read_bytes()
        cr3=struct.unpack_from('<Q',tasks,16)[0]
        if cr3:
            address=cr3&0x000ffffffffff000
            for level,shift in enumerate((39,30,21,12)):
                path=out/('vga-page-'+str(level)+'.bin')
                qmp.call('pmemsave',dict(val=address,size=4096,filename=str(path)))
                entry=struct.unpack_from('<Q',path.read_bytes(),((0xffffffff800b8000>>shift)&511)*8)[0]
                check.need(entry&1 and not entry&4,'present supervisor-only VGA page walk')
                if level<3:check.need(not entry&128,'VGA uses exact small page');address=entry&0x000ffffffffff000
                else:check.need(entry&0x800000000000001b==0x800000000000001b and entry&0x000ffffffffff000==0xb8000,
                                'VGA exact writable NX cache-disabled physical page')
        qmp.call('screendump',dict(filename=str(out/'screen.ppm')))
        cells=(out/'cells.bin').read_bytes()
        rendered='\n'.join(cells[row*160:row*160+160:2].decode('cp437') for row in range(25))
        (out/'screen.txt').write_text(rendered,encoding='utf-8')
        qmp.call('cont',{})
        if label in ('command-cat','command-ls','commands'):
            rows=rendered.splitlines()[:24]
            row=max(i for i,line in enumerate(rows) if line.rstrip()=='C:\\>')
            check.need(cells[(row*80+4)*2]==32,'blank cursor target cell')
            proofs=[]
            for frame in range(8):
                time.sleep(.12)
                path=out/('cursor-'+str(frame)+'.ppm')
                qmp.call('screendump',dict(filename=str(path)))
                proofs.append(path.name)
                if cursor_pixels(path,row,4):break
            check.need(cursor_pixels(path,row,4),'hardware cursor at current prompt')
            (out/'cursor.json').write_text(json.dumps(dict(row=row,column=4,frames=proofs)))
        return out,rendered
    try:
        files=check.medium_files({n:(package/n).read_bytes() for n in check.accepted.PINS})
        medium=bios.BootMedium(package/'reist-x86_64-floppy.img',folder/'boot-medium','floppy','normal',end)
        medium.verify('before')
        fixture=data_fixture(folder,files,start,90);fixture.verify('before')
        check.need(fixture.base.read_bytes()==(package/'system.ext2').read_bytes(),'exact published data')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        name='reist-vga-'+uuid.uuid4().hex
        command=[str(boot.resolve_qemu(None)),'-name',name,'-machine','pc,accel=tcg',
                 '-cpu','qemu64','-smp','1','-m','4096','-display','none','-vga','std',
                 '-net','none','-monitor','none','-serial','stdio',
                 '-no-reboot','-no-shutdown','-S','-qmp',f'tcp:127.0.0.1:{port},server=on,wait=off',
                 *bios.boot_arguments(medium.overlay,'floppy'),*fixture.arguments(folder)]
        if case!='healthy':
            with socket.socket() as listener:
                listener.bind(('127.0.0.1',0));gdbport=listener.getsockname()[1]
            command+=['-gdb',f'tcp:127.0.0.1:{gdbport}']
        (folder/'command.json').write_text(json.dumps(command,indent=2))
        errors=(folder/'stderr.log').open('wb')
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def receive():
            try:
                used=0
                with (folder/'serial.log').open('xb',buffering=0) as log:
                    while True:
                        chunk=os.read(vm.stdout.fileno(),4096)
                        if not chunk:return
                        used+=len(chunk)
                        if used>262144:raise ValueError('serial byte limit')
                        log.write(chunk)
            except BaseException as error:reader_errors.append(str(error))
        reader=threading.Thread(target=receive,daemon=True);reader.start()
        for _ in range(100):
            check.need(vm.poll() is None,'QEMU startup')
            try:qmp=QMP(port,name,end);break
            except ConnectionRefusedError:time.sleep(.02)
        check.need(qmp is not None,'QMP startup bound')
        if case=='early':
            debugger,debuglog=early_observer(folder,gdbport,symbols)
        elif case!='healthy':
            debugger,debuglog=fault_observer(folder,gdbport,symbols,(package/'program0.prg').read_bytes(),
                                           1 if case=='crash' else 2)
        else:qmp.call('cont',{})
        for _ in range(1200):
            check.need(vm.poll() is None and time.monotonic()<end-10,'boot deadline')
            raw=serial()
            if b'Type HELP for available commands.' in raw:break
            if any(marker in raw for marker in (b'PANIC',b'_STATE_ERROR',b'MEMORY_MAP_ERROR',b'EXCEPTION_FATAL',b'PHYSICAL_MEMORY_ERROR')):break
            time.sleep(.05)
        time.sleep(.5 if case=='healthy' else .2)
        first,screen=snapshot('startup')
        if case=='early':
            marker='REIST_X86_64_PHYSICAL_MEMORY_ERROR'
            check.need(marker.encode() in serial() and marker in screen,'early fixed error visible in UART and VGA')
            check.need(b'Type HELP' not in serial(),'error halted before userspace')
            check.need(debugger.poll()==0 and (folder/'early-injection.json').exists(),'recorded early error injection')
            result['passed']=True
            return result
        state=struct.unpack('<10Q',(first/'vga.bin').read_bytes()[:80])
        result['startup_state']=state
        check.need(state[3]==2 and state[0]&0xffffffff==4,'self-tested Ring3 console')
        bda=(first/'bios.bin').read_bytes()
        check.need(bda[0x49]==3 and struct.unpack_from('<H',bda,0x4a)[0]==80 and bda[0x84]==24,'actual BIOS mode03')
        check.need('REIST OS userspace shell' in screen,'actual VGA shell greeting')
        if case!='healthy':
            for _ in range(800):
                check.need(time.monotonic()<end-10 and vm.poll() is None,'recovery deadline')
                raw=serial()
                reaps=raw.count(b'PROCESS_REAP_OK v1=04000000')
                if case=='crash' and b'VGA console recovered. Press Enter.' in raw:break
                if case=='hang' and reaps>=3:break
                if b'VGA console unavailable:' in raw:break
                time.sleep(.05)
            check.need((folder/'fault-injection.json').exists(),'recorded fault selection')
            check.need(debugger.poll()==0,'fault observer detached')
            time.sleep(.5)
            recovered,recovered_screen=snapshot('recovery')
            recovered_state=struct.unpack('<10Q',(recovered/'vga.bin').read_bytes()[:80])
            result['recovery_state']=recovered_state
            result['console_reaps']=reaps
            if case=='hang':
                check.need(reaps==3 and recovered_state[3]==1,'three fenced console generations / restart exhaustion')
                check.need('VGA CONSOLE STOPPED' in recovered_screen,'visible degraded state')
                before=raw.count(b'Built-ins:')
                vm.stdin.write(b'help\n');vm.stdin.flush()
                for _ in range(100):
                    if serial().count(b'Built-ins:')>before:break
                    time.sleep(.05)
                check.need(serial().count(b'Built-ins:')==before+1,'ordinary serial rescue remains live')
                result['passed']=True
                return result
            check.need(recovered_state[3]==2 and recovered_state[0]!=state[0] and recovered_state[2]==state[2]+1,
                       'new exact console generation and epoch after crash')
            state=recovered_state
            qmp.call('input-send-event',{'events':[dict(type='key',data=dict(down=down,key=dict(type='qcode',data='ret'))) for down in (True,False)]})
            time.sleep(.2)
        injections=[]
        for word in ('cat data.txt','ls','help','zzzz'):
            prompts=console_text(serial()).count(b'C:\\>')
            for key in (*word,'ret'):
                key={' ':'spc','.':'dot'}.get(key,key)
                args={'events':[dict(type='key',data=dict(down=down,key=dict(type='qcode',data=key))) for down in (True,False)]}
                qmp.call('input-send-event',args);injections.append(args)
                time.sleep(.08)
            command_end=min(end-10,time.monotonic()+20)
            while time.monotonic()<command_end and console_text(serial()).count(b'C:\\>')<=prompts:
                check.need(vm.poll() is None,'guest alive during command')
                time.sleep(.05)
            time.sleep(.3)
            if word in ('cat data.txt','ls'):
                _,app_screen=snapshot('command-'+word.split()[0])
                expected='REIST native application file objects' if word.startswith('cat ') else 'data.txt'
                check.need(expected in app_screen,'actual VGA application output '+word)
                check.need(expected.encode() in console_text(serial()),'actual UART application output '+word)
        (folder/'injections.json').write_text(json.dumps(injections,indent=2))
        final,screen=snapshot('commands')
        raw=serial()
        user_text=console_text(raw)
        check.need(b'zzzz' in user_text and 'zzzz' in screen,'actual PS2 command echo in VGA and UART')
        check.need(b'Bad command or program file.' in user_text and 'Bad command or program file.' in screen,
                   'actual shell error visible in VGA and UART')
        state=struct.unpack('<10Q',(final/'vga.bin').read_bytes()[:80])
        expected=result.get('recovery_state',result['startup_state'])
        check.need(state[3]==2 and state[0]==expected[0],'console stayed healthy')
        result['passed']=True
    except BaseException as error:
        result['error']=str(error)
    finally:
        if vm is not None:boot.terminate_bounded(vm)
        if reader is not None:reader.join(timeout=2)
        if debugger is not None:boot.terminate_bounded(debugger)
        if debuglog is not None:debuglog.close()
        if qmp is not None:qmp.sock.close()
        if errors is not None:errors.close()
        for resource in (medium,fixture):
            if resource is not None:
                try:resource.verify('after')
                except BaseException as error:
                    result['passed']=False;result['cleanup_error']=str(error)
        result['elapsed']=round(time.monotonic()-start,3)
        result['stopped']=vm is None or vm.poll() is not None
        (folder/'result.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',choices=('healthy','crash','hang','early'),default='healthy');args=parser.parse_args()
    result=diagnostic(args.directory,args.output,args.case)
    print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
