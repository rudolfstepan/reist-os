"""Bounded CK device inventory; actual mode-transition proof follows separately."""
from pathlib import Path
import argparse
import json
import struct
import time
import run_qemu_x86_64_vga_console as text_guest
from check_x86_64_wide_shell_media import clone


class InventoryQMP(text_guest.QMP):
    def pci(self):
        self.seq+=1
        text_guest.check.need(self.seq<=256 and time.monotonic()<self.end,'PCI inventory budget')
        self.sock.sendall((json.dumps({'execute':'query-pci','id':self.seq})+'\n').encode())
        for _ in range(32):
            reply=self.read()
            if 'event' in reply:continue
            text_guest.check.need(reply.get('id')==self.seq and isinstance(reply.get('return'),list),
                                 'read-only PCI response')
            return reply['return']
        raise ValueError('PCI event bound')


def inventory(directory,folder):
    selected=clone(text_guest,[
        ("'-display','none','-vga','std'","'-display','none','-vga','vmware'"),
        ('end=start+90','end=start+60'),
        ('qualification=False,limit=90','qualification=False,limit=60'),
        ('data_fixture(folder,files,start,90)','data_fixture(folder,files,start,60)'),
        ("check.need('REIST OS userspace shell' in screen,'actual VGA shell greeting')",
         "check.need('REIST OS userspace shell' in screen,'actual VGA shell greeting')\n"
         "        result['pci']=qmp.pci()\n        result['passed']=True\n        return result")
    ],'reist_ck_inventory')
    selected.QMP=InventoryQMP
    return selected.diagnostic(directory,folder,'healthy')


def graphics_frame(path):
    raw=Path(path).read_bytes();header=b'P6\n1024 768\n255\n'
    if not raw.startswith(header):return False
    if len(raw)!=len(header)+1024*768*3:return False
    return all(raw[len(header)+(384*1024+x)*3:len(header)+(384*1024+x)*3+3]==color
               for x,color in ((128,b'\x33\x66\x99'),(512,b'\x33\x99\x66'),(896,b'\x99\x66\x33')))


CASES={'healthy':0,'repeated':0,'prep-crash':1,'prep-hang':2,
       'graphics-crash':3,'graphics-hang':4,'return-crash':5,'return-hang':6,'exhaustion':1}

def exhaustion(vm,serial,snapshot,result,end):
    need=text_guest.check.need
    for attempt in range(3):
        prompts=text_guest.console_text(serial()).count(b'C:\\>')
        vm.stdin.write(b'video\n');vm.stdin.flush()
        deadline=min(end-10,time.monotonic()+15)
        for _ in range(300):
            need(vm.poll() is None and time.monotonic()<deadline,'bounded exhaustion command')
            if text_guest.console_text(serial()).count(b'C:\\>')>prompts:break
            time.sleep(.05)
        need(text_guest.console_text(serial()).count(b'C:\\>')==prompts+1,'exhaustion command completed')
    raw=serial()
    need(raw.count(b'VGA return: 00000000')==2 and raw.count(b'VGA return: fffffff5')==1,
         'two recovery successes then unchanged restart exhaustion')
    final,screen=snapshot('exhausted')
    state=struct.unpack('<24Q',(final/'mode.bin').read_bytes())
    need(all(a^b==0xffffffffffffffff for a,b in zip(state[:12],state[12:])), 'exhaustion mode seal')
    need(state[3]==0 and state[4]==1 and state[9]==0,'exhausted mode safely fenced')
    need((final/'display-boot.bin').read_bytes()==bytes(32) and
         struct.unpack_from('<Q',(final/'mode-pdpt.bin').read_bytes(),509*8)[0]==0,'exhausted graphics unmapped')
    vga=struct.unpack('<10Q',(final/'vga.bin').read_bytes()[:80])
    need(vga[3]==1 and 'VGA CONSOLE STOPPED' in screen,'visible exhausted VGA state')
    before=raw.count(b'Built-ins:')
    vm.stdin.write(b'help\n');vm.stdin.flush()
    for _ in range(100):
        need(time.monotonic()<end-5 and vm.poll() is None,'rescue deadline')
        if serial().count(b'Built-ins:')>before:break
        time.sleep(.05)
    need(serial().count(b'Built-ins:')==before+1,'COM1 recovery shell survives exhaustion')
    result['passed']=True
    return result

def diagnostic(directory,folder,case='healthy'):
    text_guest.check.need(case in CASES,'CK diagnostic case')
    fault_mode=CASES[case]
    commands=('cat data.txt','ls','video',*(['video'] if case=='repeated' else []),'help','zzzz')
    selected=clone(text_guest,[
        ('import check_x86_64_vga_console_media as check','import check_x86_64_video_mode_media as check'),
        ("'-display','none','-vga','std'","'-display','none','-vga','vmware'"),
        ('for n in check.accepted.PINS','for n in check.INPUT_NAMES'),
        ("injections=[]",
         "if mode_case=='exhaustion':\n"
         "            check.need(debugger.poll()==0 and (folder/'fault-injection.json').exists(),'recorded exhaustion injection')\n"
         "            return exhaustion(vm,serial,snapshot,result,end)\n"
         "        injections=[]\n        mode_frames=[]\n        mode_groups=[]\n        graphics_snapshot=False"),
        ("for word in ('cat data.txt','ls','help','zzzz'):",
         "for word in "+repr(commands)+":\n            video_frames_start=len(mode_frames)"),
        ("time.sleep(.3)\n            if word in ('cat data.txt','ls'):",
         "time.sleep(.3)\n            if word=='video':mode_groups.append(mode_frames[video_frames_start:])\n"
         "            if word in ('cat data.txt','ls'):"),
        ("signature=struct.pack('<4Q',0x31414756434a5253,1,0,0)","signature=struct.pack('<4Q',0x3145444f4d564b43,1,0,0)"),
        ("if before!=struct.pack('<4Q',0x31414756434a5253,1,0,0)","if before!=struct.pack('<4Q',0x3145444f4d564b43,1,0,0)"),
        ("assert after==struct.pack('<4Q',0x31414756434a5253,1,cfg['mode'],0)","assert after==struct.pack('<4Q',0x3145444f4d564b43,1,cfg['mode'],0)"),
        ('mode in (1,2)','mode in (1,2,3,4,5,6)'),
        ("if case!='healthy':\n            with socket.socket()",
         "if fault_mode:\n            with socket.socket()"),
        ("if case=='early':\n            debugger,debuglog=early_observer(folder,gdbport,symbols)\n"
         "        elif case!='healthy':\n            debugger,debuglog=fault_observer(folder,gdbport,symbols,(package/'program0.prg').read_bytes(),\n"
         "                                           1 if case=='crash' else 2)",
         "if fault_mode:\n            debugger,debuglog=fault_observer(folder,gdbport,symbols,(package/'program0.prg').read_bytes(),fault_mode)"),
        ("result=dict(passed=False,qualification=False,limit=90,package=str(package),case=case)",
         "result=dict(passed=False,qualification=False,limit=90,package=str(package),case=mode_case)"),
        ("def serial():",
         "core_symbols=check.payload.elf((package/check.CORE).read_bytes(),64)['symbols']\n"
         "    symbols['mode_state']=core_symbols['native_video_state']['value']-0xffffffff80000000\n"
         "    def serial():"),
        ("('cells',0xb8000,4000)",
         "('mode',symbols['mode_state'],192),('display',symbols['native_display_state'],128),"
         "('display-boot',symbols['native_display_boot'],32),('mode-pdpt',symbols['pdpt_table'],4096),('cells',0xb8000,4000)"),
        ("tasks=(out/'tasks.bin').read_bytes()",
         "if label=='graphics':\n"
         "            for name,size in (('native_display_pd',4096),('native_display_pts',24576),('native_video_fifo_pt',4096)):\n"
         "                qmp.call('pmemsave',dict(val=symbols[name],size=size,filename=str(out/(name+'.bin'))))\n"
         "        tasks=(out/'tasks.bin').read_bytes()"),
        ("check.need(vm.poll() is None,'guest alive during command')",
         "check.need(vm.poll() is None,'guest alive during command')\n"
         "                if word=='video' and len(mode_frames)<40:\n"
         "                    frame=folder/('mode-'+str(len(mode_frames))+'.ppm')\n"
         "                    qmp.call('screendump',dict(filename=str(frame)))\n"
         "                    mode_frames.append(frame.name)\n"
         "                    if not graphics_snapshot and frame.read_bytes().startswith(b'P6\\n1024 768\\n255\\n'):\n"
         "                        snapshot('graphics');graphics_snapshot=True\n"
         "                    time.sleep(.3 if mode_case=='repeated' else .1)"),
        ("(folder/'injections.json').write_text(json.dumps(injections,indent=2))",
         "(folder/'injections.json').write_text(json.dumps(injections,indent=2))\n"
         "        result['mode_frames']=mode_frames\n        result['mode_groups']=mode_groups"),
        ("final,screen=snapshot('commands')",
         "final,screen=snapshot('commands')\n"
         "        if not fault_mode:check.need(any(graphics_frame(folder/name) for name in mode_frames),'actual three-band SVGA pixels')\n"
         "        if fault_mode:check.need(debugger.poll()==0 and (folder/'fault-injection.json').exists(),'completed recorded CK injection')\n"
         "        if fault_mode>=3:check.need(graphics_snapshot,'fault case actually reached graphics mode')\n"
         "        mode_state=struct.unpack('<24Q',(final/'mode.bin').read_bytes())\n"
         "        check.need(all(a^b==0xffffffffffffffff for a,b in zip(mode_state[:12],mode_state[12:])),'mode state seal')\n"
         "        check.need(mode_state[3]==0 and mode_state[4]==1 and mode_state[9]==0,'mode fenced and healthy text return')\n"
         "        check.need((final/'display-boot.bin').read_bytes()==bytes(32),'revoked graphics descriptor')\n"
         "        check.need(struct.unpack_from('<Q',(final/'mode-pdpt.bin').read_bytes(),509*8)[0]==0,'graphics mapping removed')"),
        ("state[3]==2 and state[0]==expected[0],'console stayed healthy'",
         "state[3]==2 and state[0]!=expected[0] and state[2]==expected[2]+(2 if mode_case=='repeated' else 1),'new console generation after mode return'")
    ],'reist_ck_mode_diagnostic')
    selected.graphics_frame=graphics_frame
    selected.exhaustion=exhaustion
    selected.fault_mode=fault_mode;selected.mode_case=case
    import run_qemu_x86_64_cli_media as cli_guest
    from build_x86_64_video_mode_media import data as mode_data
    selected.data_fixture=cli_guest.bb.function(cli_guest.data_fixture,
        dict(vars(cli_guest),mode_data=mode_data),[
            ('limit in (20,30,320,330)','limit==90'),
            ("apps.media.image('ext2-1k',files)","mode_data.image('ext2-1k',files)")])
    return selected.diagnostic(directory,folder,'healthy')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--inventory',action='store_true')
    parser.add_argument('--case',choices=tuple(CASES),default='healthy')
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=inventory(args.directory,args.output) if args.inventory else diagnostic(args.directory,args.output,args.case)
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)
