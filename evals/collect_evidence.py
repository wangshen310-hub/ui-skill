#!/usr/bin/env python3
"""Archive selected UI evaluation evidence; never grade design quality."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', type=Path, required=True)
    parser.add_argument('--revision', required=True, help='Declared source revision; hashes identify the actual files.')
    parser.add_argument('--case', required=True)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--runtime', required=True, help='Actual runtime, e.g. Chrome, Qt/X11, or design-only.')
    parser.add_argument('--artifact', action='append', required=True, metavar='LABEL=PATH')
    parser.add_argument('--out', type=Path, required=True, help='A new directory; existing evidence is never overwritten.')
    args = parser.parse_args()

    skill = args.skill.resolve()
    if not (skill / 'SKILL.md').is_file():
        parser.error('--skill must contain SKILL.md')
    if args.out.exists():
        parser.error('--out already exists; choose a new evidence directory')

    artifacts = []
    labels = set()
    for value in args.artifact:
        label, separator, raw_path = value.partition('=')
        if not separator or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', label):
            parser.error('each artifact must be LABEL=PATH with a lowercase hyphenated label')
        if label in labels:
            parser.error(f'duplicate artifact label: {label}')
        labels.add(label)
        source = Path(raw_path).resolve()
        if not source.is_file():
            parser.error(f'artifact is not a file: {source}')
        entry = {'label': label, 'source': str(source), 'sha256': sha256(source), 'bytes': source.stat().st_size}
        if source.suffix.lower() == '.png':
            with source.open('rb') as stream:
                header = stream.read(24)
            if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
                parser.error(f'PNG header is invalid: {source}')
            width, height = struct.unpack('>II', header[16:24])
            if not width or not height:
                parser.error(f'PNG dimensions are invalid: {source}')
            entry['png_size'] = {'width': width, 'height': height}
        artifacts.append((source, entry))

    runtime_files = [skill / 'SKILL.md']
    for directory in ('agents', 'references', 'scripts', 'assets'):
        base = skill / directory
        if base.is_dir():
            runtime_files.extend(path for path in sorted(base.rglob('*')) if path.is_file())
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'case': args.case,
        'target_platform': args.platform,
        'actual_runtime': args.runtime,
        'declared_skill_revision': args.revision,
        'skill_directory': str(skill),
        'skill_runtime_sha256': {str(path.relative_to(skill)): sha256(path) for path in runtime_files},
        'artifacts': [],
    }
    args.out.mkdir(parents=True, exist_ok=False)
    for source, entry in artifacts:
        target = args.out / (entry['label'] + source.suffix.lower())
        shutil.copyfile(source, target)
        if sha256(target) != entry['sha256']:
            raise RuntimeError(f'artifact changed during collection: {source}')
        entry['stored_file'] = target.name
        manifest['artifacts'].append(entry)
    destination = args.out / 'manifest.json'
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'manifest': str(destination), 'files': len(artifacts), 'quality_verdict': 'not assessed'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
