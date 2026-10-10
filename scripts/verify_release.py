#!/usr/bin/env python3
"""Portable exact-layout submission integrity, not a rights/signoff approval."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

import yaml
from row16_provider_acceptance import assess

TOP = 'tt_um_hardlpu_row16'
ACTION = 'e013b994dc124e6bbce5e4ae54d93908ac98141e'
SUPPORT = '01d5d2814fa9dd61e9d211e0b235a4a592a9316a'
APACHE_SHA = 'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'
MAIN_LICENSE_SHA = 'c4a5af90b83cd677f9277bb27d745af01f7c2672aa3fb5709d11b887f959290a'
PAYLOAD = {'.gds': 'gds', '.lef': 'lef', '.v': 'netlist',
           '.min.spef': 'spef', '.nom.spef': 'spef', '.max.spef': 'spef'}
REQUIRED = {'LICENSE', 'info.yaml', 'docs/info.md', 'README.md', 'THIRD_PARTY_NOTICES.md',
            '.github/workflows/gds.yaml', '.github/workflows/docs.yaml',
            'scripts/verify_release.py', 'scripts/row16_provider_acceptance.py',
            'evidence/provider_finish.json', 'evidence/provider_finish_audit.json',
            'evidence/physical_acceptance.json',
            'src/int4_row16.sv', 'src/int4_synapse_dot4.sv', 'src/' + TOP + '.v',
            'test/tb.sv', 'test/run_tests.py', 'test/protocol.mem', 'test/Makefile'}
REQUIRED.update(folder + '/' + TOP + suffix for suffix, folder in PAYLOAD.items())


def digest(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def local_path(root, name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name
            or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts):
        raise ValueError('invalid release path')
    target = root / name
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('release path escape')
    for path in (target, *target.parents):
        if path == root: break
        if path.is_symlink(): raise ValueError('release symlink rejected')
    return target


def same_record(path, item):
    return path.is_file() and digest(path) == {k: item[k] for k in ('bytes', 'sha256')}


def verify(root, artifact=None):
    root = Path(root).resolve()
    manifest = json.loads((root / 'release_manifest.json').read_text())
    schema = manifest.get('schema')
    if schema not in ('hardlpu.exact-provider-release.v1', 'hardlpu.exact-provider-release.v2'):
        raise ValueError('wrong release schema')
    for field in ('tapeout_ready', 'submitted', 'silicon_measured'):
        if manifest.get(field) is not False:
            raise ValueError('unapproved release claim: ' + field)
    files = {}
    for item in manifest['files']:
        path = local_path(root, item['path'])
        if item['path'] in files or not same_record(path, item):
            raise ValueError('duplicate/missing/changed release file: ' + item['path'])
        files[item['path']] = item
    if not REQUIRED <= files.keys(): raise ValueError('incomplete exact release')
    info = yaml.safe_load((root / 'info.yaml').read_text())
    project = info['project']
    if (type(project.get('clock_hz')) is not int or project['clock_hz'] != 40000000
            or project.get('top_module') != TOP or project.get('tiles') != '4x2'):
        raise ValueError('wrong first-chip operating contract')
    docs = (root / 'docs/info.md').read_text()
    if 'Clock target:40MHz (25ns).' not in docs or 'Clock target:50MHz' in docs:
        raise ValueError('stale documentation clock')
    if schema.endswith('.v1'):
        if manifest.get('license_exception_approved') is not False:
            raise ValueError('unapproved release claim: license_exception_approved')
        if digest(root / 'LICENSE') != manifest['original_license']:
            raise ValueError('original license changed')
    else:
        required = {'NOTICE', 'evidence/release_authorization.json',
                    'licenses/sky130_fd_sc_hd.LICENSE', 'licenses/Qwen3.LICENSE'}
        if not required <= files.keys(): raise ValueError('missing license provenance')
        grant = json.loads((root / 'evidence/release_authorization.json').read_text())
        if (manifest.get('license_exception_approved') is not True
                or digest(root / 'LICENSE')['sha256'] != APACHE_SHA
                or manifest['original_license']['sha256'] != MAIN_LICENSE_SHA
                or grant.get('owner') != 'eljja' or grant.get('spdx') != 'Apache-2.0'
                or grant.get('scope') != 'first-chip-row16-subset-only'
                or grant.get('public_repository_approved') is not True
                or grant.get('additional_license_approved') is not True
                or grant.get('main_project_license_changed') is not False):
            raise ValueError('invalid scoped license grant')
        for key in ('provider_terms_accepted', 'payment_authorized', 'revision_submitted'):
            if grant.get(key) is not False: raise ValueError('unapproved provider transaction')
        if grant.get('gds_sha256') != digest(root / 'gds' / (TOP + '.gds'))['sha256']:
            raise ValueError('license grant candidate mismatch')
    proof = json.loads((root / 'evidence/provider_finish_audit.json').read_text())
    if (proof.get('passed') is not True or proof.get('mismatches') != []
            or proof.get('live_process_groups') != []
            or not same_record(root / 'evidence/provider_finish.json', proof['report'])):
        raise ValueError('invalid provider evidence audit')
    finish = json.loads((root / 'evidence/provider_finish.json').read_text())
    for field in ('provider_hardening_passed', 'physical_checks_passed', 'provider_precheck_passed'):
        if finish.get(field) is not True: raise ValueError('provider check missing: ' + field)
    for field, expected in (('gate_golden_cycles', 180645), ('precheck_cases', 15), ('precheck_failures', 0)):
        if type(finish.get(field)) is not int or finish[field] != expected:
            raise ValueError('incomplete provider test evidence')
    physical = root / 'evidence/physical_acceptance.json'
    if not same_record(physical, finish['physical_acceptance']):
        raise ValueError('physical acceptance identity mismatch')
    acceptance = assess(json.loads(physical.read_text())['checked_values'])
    if not acceptance['passed']: raise ValueError('physical acceptance not closed')
    for suffix, folder in PAYLOAD.items():
        source = [r for r in finish['release_artifacts'] if r['path'].endswith('/' + TOP + suffix)]
        if len(source) != 1 or not same_record(root / folder / (TOP + suffix), source[0]):
            raise ValueError('payload is not the checked candidate: ' + suffix)
    gds = yaml.safe_load((root / '.github/workflows/gds.yaml').read_text())
    steps = gds['jobs']['gds']['steps']
    custom = [s for s in steps if s.get('uses', '').startswith('TinyTapeout/tt-gds-action/custom_gds@')]
    if len(custom) != 1 or custom[0]['uses'] != 'TinyTapeout/tt-gds-action/custom_gds@' + ACTION:
        raise ValueError('exact GDS action missing')
    settings = custom[0]['with']
    expected = dict(pdk='sky130A', top_module=TOP, gds_path='gds/' + TOP + '.gds',
                    lef_path='lef/' + TOP + '.lef', verilog_path='netlist/' + TOP + '.v',
                    **{'tools-ref': SUPPORT})
    if settings != expected: raise ValueError('custom GDS action inputs changed')
    if any(s.get('uses', '').startswith('TinyTapeout/tt-gds-action@') for s in steps):
        raise ValueError('must not resynthesize the frozen ECO candidate')
    if artifact is not None:
        artifact = Path(artifact).resolve()
        for suffix in ('.gds', '.lef', '.v'):
            expected_path = root / PAYLOAD[suffix] / (TOP + suffix)
            if not same_record(local_path(artifact, TOP + suffix), digest(expected_path)):
                raise ValueError('uploaded artifact substitution: ' + suffix)
    return dict(passed=True, files=len(files), clock_hz=40000000,
                uploaded_artifact_checked=artifact is not None,
                tapeout_ready=False, submitted=False,
                license_exception_approved=schema.endswith('.v2'),
                scope='Local exact-layout identity and retained check consistency, not CI execution or release permission.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--artifact', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.artifact)))
