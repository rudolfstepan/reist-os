"""Frozen BV source, build, media and complete runtime qualification."""
from pathlib import Path
import argparse,ast,re,subprocess,hashlib,json,sys,time,tomllib,shlex
ROOT=Path(__file__).resolve().parents[1]
BASELINE='70598088'
EVIDENCE=ROOT/'build/codex-agent/r83bv-large-file'
BASE=EVIDENCE/'candidate06'
PACKAGE='R8.3bv-large-file'
OBSERVER=EVIDENCE/'build22/binary-binding.json'
RETAINED=EVIDENCE/'candidate04'
LEGACY_RETAINED=EVIDENCE/'legacy-diagnostics46-47'

def retained_binding():
 """User-approved reuse: exact guest/observer sources, tools and successful runs."""
 pins={RETAINED/'frozen.json':'89724267916519e86347ab806917b8360c32f6b0a89f7f3d5ee35f329803e8b8',
       LEGACY_RETAINED/'frozen.json':'34425a14d1f38ebd0fe638d8d489fe4ba7bddd1687c3eea8342714ec08ef7fa6',
       EVIDENCE/'host127.json':'99591d583a385973588cd1a6effd8655ebe9a58632035e050ed7a955fca0b3d9'}
 for path,expected in pins.items():need(digest(path)==expected,'BV exact retained provenance')
 old=read(RETAINED/'frozen.json');legacy=read(LEGACY_RETAINED/'frozen.json');current=sources()
 permitted={'docs/architecture/NATIVE_LARGE_FILE_CONTRACT.md','scripts/verify_x86_64_large_file.py',
            'test/test_x86_64_large_file.py'}
 for origin in (old,legacy):
  need(set(current)==set(origin['sources']) and all(current[n]==value for n,value in origin['sources'].items()
       if n not in permitted),'BV unchanged capture/guest source set')
  need(origin['head']==git('rev-parse','HEAD') and origin['tools']==tools() and
       origin['legacy']==legacy_binding(),'BV unchanged tools/base/legacy images')
 matrix=read(RETAINED/'matrix.json')
 need(matrix['closed'] and not matrix['passed'] and len(matrix['cases'])==12 and
      all(r['passed'] and r['closed'] and r['qualification'] for r in matrix['cases']),
      'BV twelve successful new-profile captures; original matrix stays failed')
 for number in (46,47):
  row=read(EVIDENCE/f'diagnostic{number}.json')
  need(row['passed'] and not row['qualification'] and row['elapsed']<=600 and
       row['result']['summary']['candidate']==pins[LEGACY_RETAINED/'frozen.json'],
       'BV exact retained legacy diagnostic provenance')
 need(read(EVIDENCE/'host127.json')['passed'] is True,'BV complete development review')
 paths=list(pins)+[RETAINED/n for n in ('matrix.json','package.json','gate-01.json','gate-02.json','gate-03.json','gate-04.json')]
 paths +=[EVIDENCE/f'diagnostic{n}.json' for n in (46,47)]
 return [link(p) for p in paths]

def retained_raw():
 return parallel_digests(p for folder in (RETAINED/'guests',LEGACY_RETAINED/'guests')
                         for p in folder.rglob('*') if p.is_file())

def parallel_digests(paths):
 """Eight readers, at most256 queued paths; identical SHA-256 for every byte."""
 from concurrent.futures import ThreadPoolExecutor
 from itertools import islice
 result={};iterator=iter(paths)
 with ThreadPoolExecutor(max_workers=8) as pool:
  while batch:=list(islice(iterator,256)):
   for path,value in zip(batch,pool.map(digest,batch)):
    name=path.relative_to(ROOT).as_posix()
    need(name not in result,'BV unique raw evidence path');result[name]=value
 return result

def need(value,message):
 if not value:raise ValueError(message)

def digest(path):
 value=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
 return value.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,sort_keys=True)
def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30).decode('utf-8').strip()
def changed():return sorted(set(git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))
def sources():return {n:digest(ROOT/n) for n in git('ls-files','--cached','--others','--exclude-standard').splitlines()}
def package_row():
 queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
 active=[p for p in queue['packages'] if p['status']=='active']
 need(queue['active_id']==PACKAGE and len(active)==1 and active[0]['id']==PACKAGE,'BV one active package')
 return active[0]
def tools():
 from verify_x86_64_input import build_tools
 from run_qemu_x86_64_large_file import observer_toolchain
 executable,firmware=observer_toolchain(OBSERVER)
 return dict(build=build_tools(),observer=link(OBSERVER),executable=link(executable),firmware=str(firmware))
def binding():
 frozen=read(BASE/'frozen.json')
 need(frozen['head']==git('rev-parse','HEAD') and frozen['package']==package_row() and
      frozen['changed']==changed() and frozen['sources']==sources() and frozen['tools']==tools() and
      frozen['legacy']==legacy_binding() and frozen['prerequisite']==link(
          ROOT/'build/codex-agent/r83by-pio-throughput/candidate08/precommit.json'),
      'BV frozen source/scope/tool binding')
 need(frozen['retained']==retained_binding(),'BV retained evidence binding')
 return frozen
def freeze():
 need(not BASE.exists() and git('rev-parse','--short=8','HEAD')==BASELINE,'BV fresh candidate/base')
 need(digest(ROOT/'build/codex-agent/r83by-pio-throughput/candidate08/precommit.json')==
      'b5f7f862b1a5d9a0879e3abb22c6fa09fdae46d4318a4d35b36237f31f085078','BV accepted BY seal')
 row=package_row();paths=changed()
 need(set(paths)<=set(row['allowed_files']) and not git('diff','--cached','--name-only'),'BV candidate scope')
 subprocess.run(['git','diff','--check'],cwd=ROOT,check=True,timeout=30)
 commands=row['targeted_tests']+row['package_tests']+row['runtime_tests']
 need(commands==['python test/test_x86_64_large_file.py -v']+
      ['python scripts/verify_x86_64_large_file.py --'+n for n in ('defaults','package','runtime','review')],
      'BV exact five frozen gates')
 save(BASE/'frozen.json',dict(head=git('rev-parse','HEAD'),package=row,changed=paths,
      sources=sources(),tools=tools(),commands=commands,limits=[900,900,900,5000,900],
      legacy=legacy_binding(),
      retained=retained_binding(),
      prerequisite=link(ROOT/'build/codex-agent/r83by-pio-throughput/candidate08/precommit.json')))
def gates():
 frozen=binding();save(BASE/'started.json',dict(commands=frozen['commands']));rows=[]
 for number,(command,limit) in enumerate(zip(frozen['commands'],frozen['limits']),1):
  binding();log=BASE/f'gate-{number:02d}.log';start=time.monotonic()
  try:
   with log.open('xb') as output:result=subprocess.run(shlex.split(command),cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,timeout=limit)
   code=result.returncode
  except subprocess.TimeoutExpired:code=124
  row=dict(command=command,limit=limit,elapsed=time.monotonic()-start,exit_code=code,passed=code==0,log=link(log))
  rows.append(row);save(BASE/f'gate-{number:02d}.json',row)
  print('LARGE_FILE_GATE',number,'PASS' if not code else 'FAIL',flush=True)
  if code:
   save(BASE/'stopped.json',dict(passed=False,gates=rows));raise ValueError('BV first failed gate '+str(number))
 save(BASE/'gates-passed.json',dict(passed=True,gates=rows))
def run(name,command,limit):
 binding();save(BASE/(name+'-started.json'),dict(command=command,limit=limit))
 log=BASE/(name+'.log');start=time.monotonic()
 with log.open('xb') as output:result=subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,timeout=limit)
 row=dict(command=command,limit=limit,elapsed=time.monotonic()-start,passed=result.returncode==0,log=link(log))
 save(BASE/(name+'.json'),row)
 need(row['passed'] and row['elapsed']<=limit,name+': '+log.read_text(errors='replace')[-1800:]);binding()
def package():
 frozen=binding();pwsh=frozen['tools']['build']['pwsh']['path']
 import run_qemu_x86_64_large_file as guest
 import check_x86_64_large_file_media as media
 images=[]
 for name,flags in (('reference',[]),('hardware',['-NativeMathHardware'])):
  folder=BASE/name
  run(name+'-build',[pwsh,'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeLargeFile',
      *flags,'-OutputDirectory',folder.relative_to(ROOT).as_posix()],300)
  image=folder/'x86_64/reist-x86_64-bootstrap.elf';guest.image_config(image);images.append(image)
 need((images[0].parent/'boot-programs.bin').read_bytes()==(images[1].parent/'boot-programs.bin').read_bytes(),
      'BV identical reference/hardware Ring3 catalog')
 normal=guest.image_config(images[0]);hardware=guest.image_config(images[1])
 need(normal[1:]==hardware[1:],'BV identical services/applications and data')
 from build_x86_64_large_image import prepare
 variants={}
 for spec in guest.CASES:
  files=guest.case_files(spec,hardware[2]);program=files['largetest.prg']
  if spec[4]!='oversize':need(prepare(program,[])==hardware[1][4],'BV all media retain complete loaded program')
  variants[spec[0]]=dict(bytes=len(program),sha256=hashlib.sha256(program).hexdigest())
 run('reference-media',[sys.executable,'scripts/build_x86_64_large_file_media.py','--input-directory',
     str(images[1].parent),'--output-directory',str(BASE/'media')],180)
 media.verify(BASE/'media')
 artifacts={p.relative_to(ROOT).as_posix():digest(p) for name in ('reference','hardware','media')
            for p in (BASE/name).rglob('*') if p.is_file() and not any('cache' in part for part in p.parts)}
 save(BASE/'package.json',dict(passed=True,image=link(images[0]),hardware=link(images[1]),variants=variants,artifacts=artifacts))

def legacy_binding():
 path=ROOT/'build/codex-agent/r83ba-wide-file/candidate12/verification-status-wide-file-final.json'
 row=read(path);need(row['accepted'] is True,'BV accepted old profiles')
 need(row['image']['sha256']=='2fb2abf870364be311cc69d2979215b9c28fb7703ed2100c5828e37db5314df9' and
      row['legacy_image']['sha256']=='4fd24f9efb40e32eddf3d8b48afcfc8a2b6180775f2506009551d38a595ffcab',
      'BV exact accepted profile1/2 images')
 retained_artifacts(ROOT,row['artifacts'])
 return dict(seal=link(path),v1=row['legacy_image'],v2=row['image'],artifacts=row['artifacts'])

def image():
 row=read(BASE/'package.json');need(row['passed'] is True,'BV passed package')
 path=ROOT/row['hardware']['path'];need(link(path)==row['hardware'],'BV bound executing image')
 return path

def legacy_runtime(version):
 import inspect
 import run_qemu_x86_64_wide_file as wide
 module=wide.old if version=='v1' else wide
 cases=((2,2,4096),) if version=='v1' else (('legacy-v2',3,3,4096,False),)
 namespace=dict(vars(module),CASES=cases)
 exec(compile(inspect.getsource(module.run_matrix),'<BV-declared-legacy-reference>','exec'),namespace)
 start=time.monotonic();folder=BASE/'guests'/('legacy-'+version)
 binding()
 summary=namespace['run_matrix'](ROOT/legacy_binding()[version]['path'],folder,digest(BASE/'frozen.json'),binding)
 elapsed=time.monotonic()-start
 need(summary['passed'] and summary['closed'] and len(summary['cases'])==1 and elapsed<=600,'BV one bounded old-profile reference')
 return dict(label='legacy-'+version,version=version,elapsed=elapsed,passed=True,closed=True,summary=summary)

def replay_legacy(row):
 import run_qemu_x86_64_wide_file as wide
 need(row['version'] in ('v1','v2') and row['passed'] and row['closed'] and row['elapsed']<=600,'BV legacy extent')
 module=wide.old if row['version']=='v1' else wide.namespace()
 img=ROOT/legacy_binding()[row['version']]['path'];summary=row['summary']
 need(summary['passed'] and summary['closed'] and summary['image_sha256']==digest(img) and len(summary['cases'])==1,'BV fresh exact legacy image')
 item=summary['cases'][0];need((item['case'],item['layout'],item['ram'])==
      ((2,2,4096) if row['version']=='v1' else (3,3,4096)),'BV declared old case')
 config,records,app=module.image_config(img)
 need(module.evaluate(ROOT/item['folder'],config,records,(img.parent/'boot-programs.bin').read_bytes(),
      item['case'],item['layout'],app)==item['proof'],'BV complete legacy replay')

def runtime():
 """Admit the explicitly approved fourteen retained runs without a VM restart."""
 import run_qemu_x86_64_large_file as guest
 binding();img=image();old=read(RETAINED/'matrix.json')
 need(digest(img)==read(RETAINED/'package.json')['hardware']['sha256'],'BV identical executing image')
 retained_artifacts(ROOT,read(RETAINED/'package.json')['artifacts'])
 rows=list(old['cases'])+[read(EVIDENCE/f'diagnostic{n}.json')['result'] for n in (46,47)]
 labels=[s[0] for s in guest.CASES]+['legacy-v1','legacy-v2']
 need(len(rows)==14 and sorted(r['label'] for r in rows)==sorted(labels),'BV exact retained case set')
 rows.sort(key=lambda row:labels.index(row['label']))
 elapsed=sum(r['elapsed'] for r in rows)
 need(elapsed<=4200 and all(r['passed'] and r['closed'] and r['elapsed']<=600 for r in rows),'BV unchanged timing gates')
 save(BASE/'retained-raw.json',retained_raw())
 save(BASE/'matrix.json',dict(passed=True,closed=True,cases=rows,guest_elapsed=elapsed,
      retained=True,provenance=retained_binding(),original_matrix=link(RETAINED/'matrix.json'),
      original_execution_order=old['execution_order'],new_guest_starts=0))
 print('LARGE_FILE_RETAINED_ADMISSION_OK',len(rows),round(elapsed,3))


def review():
 import run_qemu_x86_64_large_file as guest
 frozen=binding();img=image();matrix=read(BASE/'matrix.json')
 need(matrix['passed'] and matrix['closed'] and len(matrix['cases'])==14 and
      matrix['guest_elapsed']<=4200,'BV complete accepted matrix')
 need(matrix['retained'] is True and matrix['new_guest_starts']==0 and
      matrix['provenance']==retained_binding(),'BV explicit retained authority and provenance')
 for spec,row in zip(guest.CASES,matrix['cases'][:12]):
  need(tuple(row[n] for n in ('label','case','layout','ram','mode'))==spec and row['passed'] and
       row['closed'] and row['qualification'] and row['elapsed']<=600 and row['image_sha256']==digest(img),
       'BV exact fresh case '+spec[0])
  folder=RETAINED/'guests'/spec[0]
  need(read(folder/'result.json')==row,'BV guest receipt binding')
  need(guest.replay_case(img,folder,spec)==row['proof'],'BV full independent case replay '+spec[0])
  config,_,_=guest.image_config(img)
  need(guest.hardware_proof(folder,config)==row['hardware'] and
       guest.audit_native_calibration(folder)==row['native_calibration'],'BV raw observer/bootstrap replay')
  if spec==guest.CASES[0]:
   need(row.get('signed') is True,'BV actual signed BIOS execution')
   guest.bios.validate_bios((folder/'guest.log').read_text(encoding='ascii'),'hdd','normal')
   command=read(folder/'command.json')
   need('-kernel' not in command and 'ide-hd,drive=az-boot,bus=ide.0,unit=1,bootindex=1' in command,'BV BIOS device boot')
   before=read(folder/'boot-medium/before.json');after=read(folder/'boot-medium/after.json')
   need(before['passed'] and after['passed'] and before['base']==after['base'] and
        before['overlay_allocated_data']==after['overlay_allocated_data']==0,'BV unchanged signed boot disk')
  print('LARGE_FILE_REPLAY_PASS',spec[0],flush=True)
 need([r['version'] for r in matrix['cases'][12:]]==['v1','v2'],'BV both old references')
 for row in matrix['cases'][12:]:replay_legacy(row)
 retained_artifacts(ROOT,read(BASE/'package.json')['artifacts'])
 need(set(changed())<=set(package_row()['allowed_files']) and not git('diff','--cached','--name-only'),'BV final scope')
 subprocess.run(['git','diff','--check'],cwd=ROOT,check=True,timeout=30);binding()
 raw=retained_raw()
 need(raw==read(BASE/'retained-raw.json'),'BV unchanged complete raw evidence throughout replay')
 save(BASE/'acceptance-seal.json',dict(passed=True,frozen=frozen,package=read(BASE/'package.json'),raw=raw,
      matrix=matrix,gates=[read(BASE/f'gate-{n:02d}.json') for n in range(1,5)]))
 print('LARGE_FILE_REVIEW_OK')

def original(name):return subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,timeout=15).decode('utf-8').replace('\r\n','\n')

def disabled(source):
 lines=source.splitlines(keepends=True);out=[];i=0
 while i<len(lines):
  line=lines[i];i+=1
  if line.strip()!='#ifdef REIST_NATIVE_LARGE_FILE':out.append(line);continue
  depth=1;take=False;elif_branch=False
  while depth:
   line=lines[i];i+=1;word=line.strip()
   if word.startswith('#if'):depth+=1
   if word=='#endif':
    depth-=1
    if depth==0:
     if elif_branch:out.append(line)
     break
   if depth==1 and word=='#else':
    if elif_branch:out.append(line)
    take=True;continue
   if depth==1 and word.startswith('#elif '):
    need(not take,'single selected alternate');take=True;elif_branch=True
    out.append(line.replace('#elif defined(', '#ifdef ').replace(')\n','\n'));continue
   if take:out.append(line)
 return ''.join(out)

def projection():
 files=('userspace/sdk/include/reist/x86_64/block.h','userspace/sdk/include/reist/x86_64/filesystem.h',
  'userspace/sdk/include/reist/x86_64/file_image.h','userspace/sdk/include/reist/x86_64/service_session.h',
  'userspace/drivers/ata/native_service.h','userspace/drivers/ata/native_service.c',
  'userspace/storage/lib/native_block.c','userspace/storage/lib/native_filesystem.c',
  'userspace/sdk/lib/x86_64/file_image.c','userspace/sdk/lib/x86_64/service_session.c',
  'userspace/sdk/lib/x86_64/shell_session.c','arch/x86_64/user/filesystem.c')
 compact=lambda s:re.sub(r'\s+','',s)
 for name in files:
  after=disabled((ROOT/name).read_text(encoding='utf-8'))
  if name.endswith('file_image.c'):
   after=after.replace('    const size_t prepared_bytes=REIST_X64_PREPARED_V2_BYTES;\n','').replace('(unsigned)prepared_bytes','REIST_X64_PREPARED_V2_BYTES').replace('prepared_bytes','REIST_X64_PREPARED_V2_BYTES')
  if name.endswith('native_service.c'):
   after=after.replace('int status;\n    status=','int status=')
  if name.endswith('service_session.c'):
   helper='static unsigned service_sectors(unsigned version,unsigned layout) {\n    return layout==0?2880U:layout==1?70000U:version==2?2048U:256U;\n}\n'
   need(after.count(helper)==1,'exact previous geometry adapter');after=after.replace(helper,'')
   after=after.replace('service_sectors(s->version,s->layout)','(s->layout==0?2880U:s->layout==1?70000U:s->version==2?2048U:256U)')
   after=after.replace('service_sectors(version,s->layout)','(s->layout==0?2880U:s->layout==1?70000U:version==2?2048U:256U)')
   # service_valid closes the accepted set to1/2; open additionally requires
   # exact public entry-point version before either comparison is evaluated.
   after=after.replace('version>=2','version==2')
  if name.endswith('shell_session.c'):
   after=after.replace('#ifndef SESSION_PREPARED_BYTES\n#define SESSION_PREPARED_BYTES REIST_X64_PREPARED_V2_BYTES\n#endif\n','').replace('SESSION_PREPARED_BYTES','REIST_X64_PREPARED_V2_BYTES')
  if name=='arch/x86_64/user/filesystem.c':
   after=after.replace('#define CAPTURE_BLOCK_REQUESTS REIST_WIDE_BLOCK_REQUESTS\n','').replace('#define CAPTURE_FS_REQUESTS REIST_WIDE_FS_REQUESTS\n','').replace('CAPTURE_BLOCK_REQUESTS','REIST_WIDE_BLOCK_REQUESTS').replace('CAPTURE_FS_REQUESTS','REIST_WIDE_FS_REQUESTS')
  need(compact(after)==compact(original(name)),'exact disabled source '+name)
 return dict(passed=True,files=list(files))

def build_projection():
 """Compare complete old build paths after selecting only LARGE_FILE=false."""
 def remove(source,text):
  need(source.count(text)==1,'exact build addition '+text[:70]);return source.replace(text,'')
 name='scripts/build-x86_64-bootstrap.ps1';source=(ROOT/name).read_text(encoding='utf-8')
 for addition in ('    [switch]$NativeLargeFile,\n',
   'if ($NativeLargeFile) { $NativeLargeImage = [switch]$true; $NativeText = [switch]$true }\n',
   '        "X86_64_NATIVE_LARGE_FILE=$([int]$NativeLargeFile.IsPresent)" `\n'):
  source=remove(source,addition)
 need(source==original(name),'entire disabled Windows build')
 name='Makefile';source=(ROOT/name).read_text(encoding='utf-8')
 begin=source.index('# Explicit large capture requires');end=source.index('# Explicit larger prepared imports;',begin)
 block=source[begin:end]
 need(block=='''# Explicit large capture requires the accepted ordinary text shell composition.
X86_64_NATIVE_LARGE_FILE ?= 0
ifneq ($(words $(X86_64_NATIVE_LARGE_FILE)),1)
$(error NativeLargeFile selector must be one value)
endif
ifneq ($(filter $(X86_64_NATIVE_LARGE_FILE),0 1),$(X86_64_NATIVE_LARGE_FILE))
$(error NativeLargeFile selector must be 0 or 1)
endif
ifeq ($(X86_64_NATIVE_LARGE_FILE),1)
X86_64_NATIVE_LARGE_IMAGE := 1
X86_64_NATIVE_TEXT := 1
endif
''','strict additive Make selector')
 source=remove(source,block)
 source=remove(source,'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_LARGE_FILE)),--large-file,)\n')
 source=remove(source,''' .PHONY: x86_64-large-file-media
X86_64_LARGE_FILE_MEDIA_INPUT ?= $(X86_64_BOOTSTRAP_DIR)
X86_64_LARGE_FILE_MEDIA_OUTPUT ?= build/codex-agent/native-large-file-media
x86_64-large-file-media:
	@$(PYTHON) scripts/build_x86_64_large_file_media.py --input-directory "$(X86_64_LARGE_FILE_MEDIA_INPUT)" --output-directory "$(X86_64_LARGE_FILE_MEDIA_OUTPUT)" --nasm "$(AS)" --openssl "$(OPENSSL)"

'''.lstrip())
 need(source==original(name),'entire disabled Make build')
 name='scripts/build_x86_64_boot_programs.py';source=(ROOT/name).read_text(encoding='utf-8')
 source=remove(source,'    if type(large_file) is not bool or large_file and (not large_image or not text_runtime or any((display,input,graphical_session,network_session))):raise ValueError("large file requires separate large image/text shell")\n')
 source=source.replace('large image requires plain NativeWide or explicit large file','large image requires plain NativeWide')
 class Disabled(ast.NodeTransformer):
  def visit_FunctionDef(self,node):
   if node.name=='build':
    need(node.args.args[-1].arg=='large_file' and node.args.defaults[-1].value is False,'explicit false default')
    node.args.args.pop();node.args.defaults.pop()
   return self.generic_visit(node)
  def visit_Name(self,node):
   return ast.Constant(False) if node.id=='large_file' else node
  def visit_UnaryOp(self,node):
   self.generic_visit(node)
   return ast.Constant(not node.operand.value) if isinstance(node.op,ast.Not) and isinstance(node.operand,ast.Constant) else node
  def visit_BoolOp(self,node):
   self.generic_visit(node)
   if isinstance(node.op,ast.And):
    if any(isinstance(v,ast.Constant) and v.value is False for v in node.values):return ast.Constant(False)
    node.values=[v for v in node.values if not (isinstance(v,ast.Constant) and v.value is True)]
   if len(node.values)==1:return node.values[0]
   return node
  def visit_If(self,node):
   self.generic_visit(node)
   if isinstance(node.test,ast.Constant):return node.body if node.test.value else node.orelse
   return node
  def visit_Expr(self,node):
   if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='add_argument' and node.value.args and isinstance(node.value.args[0],ast.Constant) and node.value.args[0].value=='--large-file':return None
   return self.generic_visit(node)
  def visit_Call(self,node):
   if isinstance(node.func,ast.Name) and node.func.id=='build':
    need(isinstance(node.args[-1],ast.Attribute) and node.args[-1].attr=='large_file','last builder argument');node.args.pop()
   if isinstance(node.func,ast.Attribute) and node.func.attr=='mkdir':
    node.keywords=[k for k in node.keywords if not (k.arg=='exist_ok' and isinstance(k.value,ast.Name) and k.value.id=='large_file')]
   return self.generic_visit(node)
 actual=Disabled().visit(ast.parse(source))
 need(ast.dump(actual)==ast.dump(ast.parse(original(name))),'entire disabled Python builder')
 return dict(passed=True,files=['Makefile','scripts/build-x86_64-bootstrap.ps1',name])

def retained_artifacts(root, artifacts):
 """Hash exact retained files without admitting paths outside the workspace."""
 root=Path(root).resolve()
 need(type(artifacts) is dict and 0<len(artifacts)<=32768,'retained artifact inventory')
 for name,expected in artifacts.items():
  need(type(name) is str and not Path(name).is_absolute() and
       type(expected) is str and re.fullmatch('[0-9a-f]{64}',expected),'retained artifact identity')
  path=root/name
  need(path.resolve().is_relative_to(root) and not path.is_symlink() and
       path.is_file() and path.stat().st_size<=512*1024*1024,'retained artifact path/extent')
  digest=hashlib.sha256()
  with path.open('rb') as stream:
   for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
  need(digest.hexdigest()==expected,'retained artifact changed '+name)
 return len(artifacts)

def defaults():
 """Frozen gate2: disabled paths, old-profile behavior and accepted artifacts."""
 binding()
 projection();build_projection()
 for name in ('test/test_x86_64_wide_file.py','scripts/verify_x86_64_reference_artifacts.py'):
  subprocess.run([sys.executable,name],cwd=ROOT,timeout=300,check=True)
 retained=0
 for name in ('r83bi-graphical-session/development-build07.json',
              'r83bk-network-fatal/build01.json','r83bl-network-session/build14.json'):
  path=ROOT/'build/codex-agent'/name
  need(path.stat().st_size<=4*1024*1024,'retained receipt extent')
  retained+=retained_artifacts(ROOT,json.loads(path.read_text())['artifacts'])
 for name in ('r83bm-application-udp/candidate04','r83bn-application-tcp/candidate06',
              'r83bp-application-dns/candidate04','r83bq-application-http/candidate01',
              'r83br-cpp-runtime/candidate01','r83bs-native-math/candidate07',
              'r83bt-native-text/candidate03','r83bu-large-image/candidate01'):
  path=ROOT/'build/codex-agent'/name/'acceptance-seal.json'
  # Accepted math/text seals contain complete raw-evidence inventories
  # (currently up to9.3MB); do not confuse these with small build receipts.
  need(path.stat().st_size<=16*1024*1024,'retained seal extent')
  seal=json.loads(path.read_text());need(seal['passed'] is True,'accepted predecessor')
  retained+=retained_artifacts(ROOT,seal['package']['artifacts'])
 print('LARGE_FILE_DEFAULTS_OK',retained)

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
 for name in ('projection','defaults','freeze','gates','package','runtime','review'):g.add_argument('--'+name,action='store_true')
 a=p.parse_args()
 print(globals()[next(name for name,value in vars(a).items() if value)]())
