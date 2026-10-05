"""Require the declared scientific rejection, not an unrelated runtime zero."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
EXPECTED={
 'empty':r'discovery: missing keys',
 'naive_axis':r'axis stationary separation',
 'heldout_informed_support':r'discovery\.support: list dimensions',
 'fabricated_high_transfer':r'evaluation\.people\.sub-pixar\d+\.transfer\.fraction: numerical disagreement',
 'heldout_optimal_axis_substitution':r'evaluation\.people\.sub-pixar\d+\.transfer\.(rayleigh|fraction): numerical disagreement',
 'blanket_unjustified_null':r'evaluation\.people\.sub-pixar\d+\.transfer: missing keys',
 'missing_person':r'evaluation\.people: missing keys',
 'incorrect_network_interpretation':r'discovery\.configuration: categorical/integer disagreement',
}

def audit():
    out=[]
    for case,pattern in EXPECTED.items():
        paths=list((ROOT/'jobs'/('control-'+case+'-v3')).glob('*/verifier/receipt.json'))
        assert len(paths)==1,(case,paths)
        value=json.loads(paths[0].read_text())
        assert value['status']=='rejected' and value['exception_type']=='ValueError',value
        assert re.fullmatch(pattern,value['error']),(case,value['error'])
        if case in ('empty','naive_axis','heldout_informed_support','incorrect_network_interpretation'):
            assert not paths[0].with_name('candidate-stdout.txt').exists(), 'uncertified discovery executed'
        out.append({'case':case,'intended_rejection_verified':True,'error':value['error']})
    return out

if __name__=='__main__':
    result=audit()
    with (ROOT/'intended_rejections.json').open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))
