"""Atomic archive publication with the destination directory's normal ACL.

Python's private Windows temporary directories intentionally restrict access.
Moving an archive out of them retains that DACL. Copy bytes, not permissions,
into an ordinary exclusively created sibling before the same-directory replace.
No permission grants, ACL resets, ownership changes or retries belong here.
"""
import os
from pathlib import Path
import uuid

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


def _copy_archive(source, target, size):
    remaining = size
    while remaining:
        block = source.read(min(1024 * 1024, remaining))
        if not block:
            raise ValueError('archive truncated during publication')
        target.write(block)
        remaining -= len(block)
    if source.read(1):
        raise ValueError('archive grew during publication')


def publish_archive(source, destination):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve() or (
            destination.exists() and os.path.samefile(source,destination)):
        raise ValueError('archive publication requires distinct files')
    with source.open('rb') as incoming:
        size = os.fstat(incoming.fileno()).st_size
        if not 8 <= size <= MAX_ARCHIVE_BYTES or incoming.read(8) != b'!<arch>\n':
            raise ValueError('invalid or oversized SDK archive')
        incoming.seek(0)
        destination.parent.mkdir(parents=True,exist_ok=True)
        stage = destination.with_name('.'+destination.name+'.publish-'+uuid.uuid4().hex+'.tmp')
        created = False
        try:
            # Not tempfile/mkstemp: those deliberately request private ACLs.
            with stage.open('xb') as outgoing:
                created = True
                _copy_archive(incoming,outgoing,size)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            os.replace(stage,destination)
            created = False
        finally:
            if created:
                stage.unlink(missing_ok=True)
