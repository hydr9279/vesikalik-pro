import sys, glob, numpy as np, cv2
sys.path.insert(0,'/home/claude/vp')
from engine.job import Job
from engine import face as F
for f in sorted(glob.glob('/home/claude/ornekler/orijinal/*.JPG'))+['/home/claude/ornekler/ham_07.jpg','/home/claude/ornekler/ham_02.jpg']:
    j=Job(f); j.analyze(); L=j.labels; iod=j.iod
    def ext(c):
        ys,xs=np.nonzero(L==c); return (ys.max()-ys.min()+1)/iod if len(ys) else 0
    nose_u=F.apply(j.R,j.nose); e_u=F.apply(j.R,j.eye_mid)
    sk=(L==F.SKIN); ys,xs=np.nonzero(sk)
    # face width symmetry: skin left/right extent around eye mid in upright
    print(j.name, 'eyeH', round(ext(F.LEYE),3), round(ext(F.REYE),3), 'eyeA', round((L==F.LEYE).sum()/iod**2,4), round((L==F.REYE).sum()/iod**2,4),
      'mouth', round((L==F.MOUTH).sum()/iod**2,4), 'nose dx', round((nose_u[0]-e_u[0])/iod,3), 'nose raw', j.nose, 'eyemid', j.eye_mid, 'glass', round((L==F.GLASSES).sum()/iod**2,3))
