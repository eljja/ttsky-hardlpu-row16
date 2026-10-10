#!/usr/bin/env python3
"""Standalone RTL or zero-delay powered-netlist pin regression, with JUnit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

MARKER='CHIP_ACCESS cycles=180645 pass=180645'


def identity(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def power_name(text):
    header=text.split('endmodule')[0].split('module tt_um_hardlpu_row16',1)[1]
    names=re.findall(r'\b(?:input|inout)\s+(?:wire\s+)?(VPWR|VDPWR)\b',header)
    if len(names)!=1:raise ValueError('missing/ambiguous top power pin')
    return names[0]


def run(args,folder,label,limit):
    with (folder/(label+'.stdout.log')).open('w') as stdout,(folder/(label+'.stderr.log')).open('w') as stderr:
        child=subprocess.Popen([str(x) for x in args],cwd=folder,stdout=stdout,stderr=stderr,start_new_session=True)
        timeout=False
        try:code=child.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timeout=True;os.killpg(child.pid,signal.SIGTERM)
            try:code=child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
    result=dict(args=[str(x) for x in args],exit_code=code,timeout=timeout,joined=True,limit_seconds=limit,
                logs=[identity(folder/(label+x)) for x in ('.stdout.log','.stderr.log')])
    (folder/(label+'.execution.json')).write_text(json.dumps(result,indent=2)+'\n')
    if timeout or code:raise RuntimeError(label+' failed; see '+str(folder))
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--netlist',type=Path);parser.add_argument('--wrong-golden',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1];test=root/'test'
    output=test/'output';output.mkdir(exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='gate-' if args.netlist else 'rtl-',dir=output))
    xml=test/'results.xml';suite=ET.Element('testsuite',name='HardLPU provider pin regression',tests='1',errors='1')
    case=ET.SubElement(suite,'testcase',name='180645 pin cycles')
    ET.SubElement(case,'error',message='Run incomplete; never reuse old PASS')
    ET.ElementTree(suite).write(xml,encoding='unicode')
    started=time.monotonic()
    try:
        tb=(test/'tb.sv').read_text();sources=[];options=[]
        if args.netlist:
            netlist=args.netlist.resolve();pdk=Path(os.environ['PDK_ROOT'])/'sky130A'
            tb=tb.replace('.VPWR(VPWR)',f'.{power_name(netlist.read_text())}(VPWR)')
            options=['-DGATE','-DFUNCTIONAL','-DUSE_POWER_PINS','-DUNIT_DELAY=#0']
            sources=[pdk/'libs.ref/sky130_fd_sc_hd/verilog/primitives.v',
                     pdk/'libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v',netlist]
        else:sources=[root/'src'/n for n in ('int4_synapse_dot4.sv','int4_row16.sv','tt_um_hardlpu_row16.v')]
        (folder/'tb.sv').write_text(tb)
        vectors=(test/'protocol.mem').read_text().splitlines()
        if len(vectors)!=180645:raise ValueError('incomplete vector set')
        if args.wrong_golden:vectors[0]=f'{int(vectors[0],16)^(1<<18):010x}'
        (folder/'protocol.mem').write_text('\n'.join(vectors)+'\n')
        stages=[run(['iverilog','-g2012',*options,'-s','tb_chip','-o',folder/'sim.vvp',*sources,folder/'tb.sv'],folder,'compile',60),
                run(['vvp',folder/'sim.vvp'],folder,'simulate',240)]
        if (folder/'simulate.stdout.log').read_text().splitlines().count(MARKER)!=1:raise ValueError('missing full pass marker')
        if args.wrong_golden:raise ValueError('negative mutation incorrectly passed')
        case.remove(case.find('error'));suite.set('errors','0');case.set('time',str(round(time.monotonic()-started,3)))
        (folder/'result.json').write_text(json.dumps(dict(passed=True,cycles=180645,stages=stages,
            inputs=[identity(p) for p in sources]+[identity(test/'protocol.mem'),identity(test/'tb.sv')],
            scope='RTL or zero-delay functional gate; not SDF timing, Fmax, power or silicon.',tapeout_ready=False),indent=2)+'\n')
        print('PROVIDER_PIN_REGRESSION_PASS cycles=180645')
    except Exception as error:
        case.find('error').set('message',str(error));raise
    finally:ET.ElementTree(suite).write(xml,encoding='unicode')


if __name__=='__main__':main()
