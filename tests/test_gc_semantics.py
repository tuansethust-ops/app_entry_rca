def classify(wait,competition,overlap):
    return 'DIRECT_BLOCK' if wait>1 else ('COMPETITION' if competition>1 else ('OVERLAP_ONLY' if overlap>0 else 'NO_GC_EVIDENCE'))

def test_gc_overlap_is_not_direct(): assert classify(0,0,500)=='OVERLAP_ONLY'
def test_gc_wait_is_direct(): assert classify(10,0,100)=='DIRECT_BLOCK'
def test_gc_competition(): assert classify(0,5,100)=='COMPETITION'
