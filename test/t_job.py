import sys, time, cv2, numpy as np
sys.path.insert(0,'/home/claude/vp')
from engine.job import Job
from engine.formats import FORMATS
from engine import models
import glob
files=sys.argv[1:] or sorted(glob.glob('/home/claude/ornekler/orijinal/*.JPG'))
outs=[]
for f in files:
    t=time.time(); j=Job(f); j.analyze(); t1=time.time()-t
    j.matte_params['model']='isnet'
    t=time.time(); j.matte(); t2=time.time()-t
    t=time.time(); j.retouch(); t3=time.time()-t
    fmt=FORMATS['bio56']
    r=j.render(fmt, preview=False)
    m=j.measures(fmt)
    print(j.name,'analyze %.1f matte %.1f retouch %.1f'%(t1,t2,t3),'angle %.1f'%j.angle, m, 'spots',len(j.spots_found),'susp',[b['ad'] for b in j.suspicious])
    print('   ', [(c['ad'],c['durum'],c['deger']) for c in j.compliance(fmt) if c['durum']!='ok'])
    outs.append(cv2.resize(r,(295,354)))
cv2.imwrite('/home/claude/vp/test/grid.jpg',np.hstack(outs))
