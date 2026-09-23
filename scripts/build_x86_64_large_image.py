"""Explicit RNPGv3 host producer, reusing the existing strict ELF algorithm."""
import inspect,struct
import build_x86_64_boot_programs as prior

def once(source,before,after):
    if source.count(before)!=1:raise ValueError('large image producer drift: '+before)
    return source.replace(before,after)

source=inspect.getsource(prior.prepare)
for before,after in (
    ('def prepare(raw,args,wide=False):','def prepare(raw,args):\n    wide=True'),
    ('slots=64 if wide else 8','slots=256'),
    ('(524288 if wide else 65536)','1048576'),
    ("b'RNPGv2\\0\\0'+struct.pack('<IIQ',2,266336,entry)",
     "b'RNPGv3\\0\\0'+struct.pack('<IIQ',3,1052960,entry)")):
    source=once(source,before,after)
exec(compile(source,'<explicit-RNPGv3-producer>','exec'),globals())
