"""Create symmetrical, continuous facial surfaces without source-mesh fragments.
Run under Python with numpy/scipy/scikit-image. Outputs NPZ for Blender.
"""
from pathlib import Path
import numpy as np
from skimage.measure import marching_cubes
from scipy.spatial import cKDTree
import json

OUT=Path(__file__).resolve().parent/'CleanFace'
OUT.mkdir(exist_ok=True)


def smooth_union(a,b,k):
    h=np.clip(.5+.5*(b-a)/k,0,1)
    return b*(1-h)+a*h-k*h*(1-h)


def ellipsoid(x,y,z,c,r):
    qx=(x-c[0])/r[0];qy=(y-c[1])/r[1];qz=(z-c[2])/r[2]
    k0=np.sqrt(qx*qx+qy*qy+qz*qz)
    k1=np.sqrt((qx/r[0])**2+(qy/r[1])**2+(qz/r[2])**2)
    return k0*(k0-1)/np.maximum(k1,1e-12)


def mouth_field(x,y,z):
    smile=.376+.009*(x/.070)**2
    opening=ellipsoid(x,y,z,(0,-.823,smile),(.068,.087,.026))
    # The muzzle makes a shallow central dip in the upper lip.
    upper_lip=.399-.010*np.exp(-(x/.023)**2)
    return -smooth_union(-opening,upper_lip-z,.004)


def eye_field(x,y,z):
    return ellipsoid(np.abs(x),y,z,(.070,-.767,.454),(.024,.035,.023))


def head_field(x,y,z):
    d=ellipsoid(x,y,z,(0,-.644,.452),(.160,.133,.145))
    d=smooth_union(d,ellipsoid(x,y,z,(0,-.650,.387),(.160,.119,.081)),.034)
    d=smooth_union(d,ellipsoid(x,y,z,(0,-.615,.235),(.192,.130,.161)),.060)
    muzzle=ellipsoid(np.abs(x),y,z,(.034,-.778,.413),(.047,.037,.030))
    d=smooth_union(d,muzzle,.026)
    # Smooth closed cavity boundaries. No deleted face patches or hanging edges.
    d=np.maximum(d,-mouth_field(x,y,z))
    d=np.maximum(d,-eye_field(x,y,z))
    return d


def extract(name,bounds,step,fn):
    axes=[np.linspace(lo,hi,round((hi-lo)/step)+1,dtype=np.float64) for lo,hi in bounds]
    spacings=tuple(float(a[1]-a[0]) for a in axes)
    volume=np.empty(tuple(map(len,axes)),np.float32)
    x=axes[0][:,None];y=axes[1][None,:]
    for k,z in enumerate(axes[2]):volume[:,:,k]=fn(x,y,z)
    verts,faces,normals,values=marching_cubes(volume,0,spacing=spacings,gradient_direction='ascent',allow_degenerate=False)
    verts+=np.array([a[0] for a in axes])
    # Numerical grid centring: force both sides to use the same exact x plane.
    verts[:,0]-=(axes[0][0]+axes[0][-1])/2
    np.savez_compressed(OUT/(name+'.npz'),vertices=verts.astype(np.float32),faces=faces)
    mirrored=verts.copy();mirrored[:,0]*=-1
    distances=cKDTree(verts).query(mirrored,workers=4)[0]
    stats={'vertices':len(verts),'triangles':len(faces),'max_mirror_error':float(distances.max()),'mean_mirror_error':float(distances.mean())}
    print(name,json.dumps(stats),flush=True)
    return stats


report={}
report['head']=extract('clean_head',[(-.225,.225),(-.925,-.43),(.055,.64)],.002,head_field)


def nose_field(x,y,z):
    # Rounded inverted triangle: wider above, narrowing towards the philtrum.
    height=(z-.427)/.022
    width=.028*(1+.25*np.clip(height,-1,1))
    d=ellipsoid(x,y,z,(0,-.821,.427),(width,.019,.0205))
    wing=ellipsoid(np.abs(x),y,z,(.019,-.824,.431),(.011,.014,.011))
    d=smooth_union(d,wing,.007)
    nx=np.abs(x)-.018;nz=z-.428
    u=.88*nx+.475*nz;v=-.475*nx+.88*nz
    nostril=ellipsoid(u,y,v,(0,-.839,0),(.0076,.009,.0036))
    d=np.maximum(d,-nostril)
    return d


report['nose']=extract('clean_nose',[(-.046,.046),(-.855,-.795),(.398,.455)],.00055,nose_field)
(OUT/'surface_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
