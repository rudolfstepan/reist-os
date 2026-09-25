"""Frozen CI qualification; exact archived desktop fixture, fresh bounded guests."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,struct,subprocess,sys,time,tomllib,zipfile
import verify_x86_64_desktop_startup as cf
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83ci-input-return'
G=BASE/'qualification01'
ARCHIVE=BASE/'before-ci01/files.zip'
SHA='28394e53e280b0031ce2c92a1c9d53c0a8f4cc9305bc710248222b0c9b9fab46'
def need(value,message):
 if not value:raise ValueError(message)
def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,value):Path(p).write_text(json.dumps(value,indent=2),encoding='utf-8')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30).decode().strip()
def fixture():
 need(digest(ARCHIVE)==SHA,'archived CB hash')
 with zipfile.ZipFile(ARCHIVE) as z:return {p:z.read(p) for p in z.namelist() if not p.startswith(('automation/','docs/'))}
def package():
 q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text());active=[p for p in q['packages'] if p['status']=='active']
 need(len(active)==1 and active[0]['id']==q['active_id']=='R8.3ci-input-return','sole active CI');return active[0]
def binding():
 p=package();allowed=set(p['allowed_files'])
 changed=set(git('diff','--name-only').splitlines())|set(git('diff','--cached','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
 need(changed<=allowed,'CI scope')
 subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,check=True,timeout=30)
 names=set(git('ls-files').splitlines())|allowed
 sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file() and (n=='Makefile' or n.startswith(('arch/','userspace/','include/','scripts/','test/','assets/','config/','kernel/','lib/','drivers/','fs/','mm/')))}
 from build_user_program import find_zig
 from run_qemu_x86_64_boot import resolve_qemu
 tools=[Path(sys.executable),Path(shutil.which('pwsh')),Path('C:/tools/nasm-3.02/nasm.exe'),Path(find_zig()),Path(resolve_qemu(None))]
 return dict(head=git('rev-parse','HEAD'),package=p,sources=sources,tools={str(t):digest(t) for t in tools},archive=SHA,fixture={n:hashlib.sha256(raw).hexdigest() for n,raw in fixture().items()},contract=digest(ROOT/'docs/architecture/NATIVE_INPUT_RETURN_CONTRACT.md'))
def unchanged():need(binding()==read(G/'binding.json'),'frozen CI inputs')
def freeze():
 need(not G.exists(),'fresh qualification');b=binding();G.mkdir();save(G/'binding.json',b)
 save(G/'gate-order.json',[*b['package']['targeted_tests'],*b['package']['package_tests'],*b['package']['runtime_tests']])
def files(folder):return {p.relative_to(folder).as_posix():digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def make_package():
 unchanged();need(not (G/'package-started.json').exists(),'package gate once');save(G/'package-started.json',dict(start=time.time()))
 with cf.overlay(fixture(),G/'package-overlay'):
  cf.run(['pwsh','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeFullDesktop','-OutputDirectory',str((G/'build').relative_to(ROOT))],G/'build.log',300)
  cf.run([sys.executable,'scripts/build_x86_64_full_desktop_media.py','--input-directory',G/'build/x86_64','--output-directory',G/'media'],G/'media.log',180)
  import check_x86_64_full_desktop_media as check
  check.verify(G/'media')
 unchanged();save(G/'package.json',dict(passed=True,build=files(G/'build'),media=files(G/'media')))
def media_unchanged():
 p=read(G/'package.json');need(p['passed'] and p['build']==files(G/'build') and p['media']==files(G/'media'),'immutable package artifacts')
def runtime():
 unchanged();media_unchanged();need(not (G/'runtime-started.json').exists(),'runtime gate once');save(G/'runtime-started.json',dict(start=time.time()))
 started=time.monotonic();rows=[]
 key='REIST_CF_QUALIFICATION_END';need(key not in os.environ,'owned guest deadline');os.environ[key]=repr(started+1500)
 try:
  with cf.overlay(fixture(),G/'runtime-overlay'):
   import run_qemu_x86_64_full_desktop as runner
   rows.append(runner.diagnostic(G/'media',G/'mouse',mouse_stress=True))
   rows.append(cf.exercise(G/'media',G/'normal'))
   # The immutable fixture is already installed; prevent the older CF archive
   # adapter from replacing it. The accepted lifecycle callback is unchanged.
   original=cf.fixture_files;cf.fixture_files=lambda:{}
   try:rows.append(cf.lifecycle_existing(G/'cpu',G,selector=9))
   finally:cf.fixture_files=original
 finally:os.environ.pop(key,None)
 need(len(rows)==3 and all(r['passed'] and r['closed'] and r['elapsed']<=600 for r in rows),'three fresh bounded guests')
 need(sum(r['elapsed'] for r in rows)<=1800 and time.monotonic()-started<=1800,'runtime aggregate')
 unchanged();media_unchanged()
 save(G/'runtime.json',dict(passed=True,elapsed=time.monotonic()-started,guests=[r['elapsed'] for r in rows],artifacts={n:files(G/n) for n in ('mouse','normal','cpu')}))
def pointer(path,x,y):
 magic,dimensions,maximum,pixels=path.read_bytes().split(b'\n',3)
 need(magic==b'P6' and dimensions==b'1024 768' and maximum==b'255' and len(pixels)==1024*768*3,'framebuffer shape')
 for dy in range(12):
  for dx in range(8):
   if not dx or not dy or dx==dy//2:
    i=((y+dy)*1024+x+dx)*3;need(pixels[i:i+3]==b'\xff'*3,'actual pointer position')
def live(folder,stages):
 owners=[cf.review_live_roles(folder/s) for s in stages];need(all(v==owners[0] for v in owners),'stable exact owners/rights/CPU budgets');return owners[0]
def review():
 unchanged();media_unchanged();r=read(G/'runtime.json');need(r['passed'],'runtime receipt')
 for n,expected in r['artifacts'].items():need(files(G/n)==expected,'raw runtime artifact hash')
 for folder in (G/'mouse',G/'normal',G/'cpu/guest'):
  row=read(folder/'result.json');need(row['passed'] and row['closed'] and row['elapsed']<=600 and row['media_before']==row['media_after'],'closed unchanged guest')
 mouse=G/'mouse';live(mouse,('desktop','mouse-stress','mouse-stable'))
 events=read(mouse/'mouse-stress-events.json');need(len(events)==801,'801 movement batches')
 for i,event in enumerate(events):
  direction=1 if i%2==0 else -1
  expected={'events':[dict(type='rel',data=dict(axis='x',value=4*direction)),dict(type='rel',data=dict(axis='y',value=2*direction))]}
  need(event['arguments']==expected,'exact alternating stress trajectory')
  if i:need(event['elapsed']>=events[i-1]['elapsed']+.01,'original stress pacing')
 pointer(mouse/'mouse-stress/pixels.ppm',516,386)
 normal=G/'normal';live(normal,('desktop','keyboard','stable'))
 need(not cf.keyboard_glyphs((normal/'text-focus/pixels.ppm').read_bytes()) and len(cf.keyboard_glyphs((normal/'keyboard/pixels.ppm').read_bytes()))==1,'exact abc pixels at original300ms')
 pointer(normal/'pointer/pixels.ppm',536,396)
 cpu=G/'cpu/guest';before=cf.review_live_roles(cpu/'desktop');after=cf.review_live_roles(cpu/'lifecycle')
 need(cf.review_live_roles(cpu/'replacement-stable')==after,'stable replacement')
 need(all(before[i]==after[i] for i in (0,1,3)) and after[2]>before[2],'isolated new text generation')
 receipts=[struct.unpack('<4I2Q',bytes.fromhex(h)) for h in re.findall(r'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-Fa-f]{64})',(cpu/'guest.log').read_text())]
 terminals=[v for v in receipts if v[:2]==(6,before[2]>>32)]
 need(len(terminals)==1 and terminals[0][2:4]==(256,3),'actual unchanged CPU fencing')
 for stage in ('lifecycle','replacement-stable'):need(len(cf.desktop_glyphs((cpu/stage/'pixels.ppm').read_bytes(),b'Type','a7bbce'))==1,'replacement scene visible')
 with cf.overlay(fixture(),G/'review-overlay'):
  import check_x86_64_full_desktop_media as check
  check.verify(G/'media')
 unchanged();save(G/'review.json',dict(passed=True,fresh_guests=3,binding=digest(G/'binding.json'),runtime=digest(G/'runtime.json'),package=digest(G/'package.json')))
if __name__=='__main__':
 parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
 for n in ('freeze','package','runtime','review'):group.add_argument('--'+n,action='store_true')
 args=parser.parse_args()
 if args.freeze:freeze()
 elif args.package:make_package()
 elif args.runtime:runtime()
 else:review()
 print('CI_GATE_PASS',flush=True)
