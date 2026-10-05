"""Photo-guided facial fields shared by geometry and surface shading."""
import numpy as np
EYE_X=.070
EYE_Z=.454
EYE_Y=-.749
EYE_RADIUS=.0255
NOSE_Z=.435


def smooth_union(a,b,k):
    h=np.clip(.5+.5*(b-a)/k,0,1)
    return b*(1-h)+a*h-k*h*(1-h)


def ellipsoid(x,y,z,c,r):
    qx=(x-c[0])/r[0];qy=(y-c[1])/r[1];qz=(z-c[2])/r[2]
    k0=np.sqrt(qx*qx+qy*qy+qz*qz)
    k1=np.sqrt((qx/r[0])**2+(qy/r[1])**2+(qz/r[2])**2)
    return k0*(k0-1)/np.maximum(k1,1e-12)


def mouth_field(x,y,z):
    opening=ellipsoid(x,y,z,(0,-.824,.375+.008*(x/.066)**2),(.066,.087,.031))
    upper=.391+.015*np.exp(-(x/.030)**2)
    return -smooth_union(-opening,upper-z,.0035)


def eye_field(x,y,z):
    dx=np.abs(x)-EYE_X
    # Palpebral opening is lower than the eyeball's full diameter.
    return ellipsoid(dx,y,z-.10*dx,(0,-.766,EYE_Z),(.0235,.034,.0205))


def head_field(x,y,z):
    d=ellipsoid(x,y,z,(0,-.642,.456),(.161,.135,.143))
    d=smooth_union(d,ellipsoid(x,y,z,(0,-.650,.386),(.161,.119,.081)),.030)
    d=smooth_union(d,ellipsoid(x,y,z,(0,-.613,.235),(.183,.132,.163)),.057)
    muzzle=ellipsoid(np.abs(x),y,z,(.032,-.781,.419),(.048,.039,.032))
    d=smooth_union(d,muzzle,.018)
    chin=ellipsoid(x,y,z,(0,-.767,.339),(.057,.042,.026))
    d=smooth_union(d,chin,.023)
    brow=ellipsoid(np.abs(x),y,z,(.074,-.742,.478),(.038,.023,.012))
    d=smooth_union(d,brow,.017)
    lowerlid=ellipsoid(np.abs(x),y,z,(.072,-.742,.434),(.032,.021,.009))
    d=smooth_union(d,lowerlid,.008)
    d=np.maximum(d,-mouth_field(x,y,z))
    d=np.maximum(d,-eye_field(x,y,z))
    return d


def nose_field(x,y,z):
    height=(z-NOSE_Z)/.027
    width=.028*(1+.26*np.clip(height,-1,1))
    d=ellipsoid(x,y,z,(0,-.823,NOSE_Z),(width,.020,.026))
    wing=ellipsoid(np.abs(x),y,z,(.020,-.825,.443),(.011,.014,.012))
    d=smooth_union(d,wing,.006)
    dx=np.abs(x)-.0175;dz=z-.442
    # Curved, near-vertical nostril recess rather than horizontal slots.
    u=.97*dx+.24*dz;v=-.24*dx+.97*dz
    nostril=ellipsoid(u,y,v,(0,-.841,0),(.0065,.010,.009))
    d=np.maximum(d,-nostril)
    return d
