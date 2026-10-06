"""Standing Ogong anatomy fitted to the user's five-view reference sheet.

Units are normalized to approximately one unit of total coat height, not metres.
The drawing's hidden joints are artistic estimates, not measured anatomy.
X = left/right, -Y = forward, +Z = up.
"""
import numpy as np
from portrait_fields import ellipsoid as ell, smooth_union as union, nose_field as old_nose

HEAD_SCALE = np.array([1.10, 1.20, 1.10])
HEAD_OFFSET = np.array([0.0, .40, .2426])
EYE_LOCAL = np.array([.070, -.749, .454])
EYE_RADIUS = .0230


def to_head(x, y, z):
    return x / 1.10, (y - .40) / 1.20, (z - .2426) / 1.10


def mouth_local(x, y, z):
    opening = ell(x, y, z, (0, -.824, .3505 + .008*(x/.072)**2), (.072, .096, .032))
    upper = .3665 + .015*np.exp(-(x/.030)**2)
    return -union(-opening, upper-z, .0035)


def closed_lip_height(x):
    """Neutral lip contact, in head-local coordinates, with a shallow central cleft."""
    return .388 + .0018*(np.abs(x)/.038)**2 - .001*np.exp(-(x/.012)**2)


def eye_local(x, y, z):
    dx = np.abs(x)-.070
    return ell(dx, y, z-.06*dx, (0, -.766, .454), (.0215, .032, .0195))


def head_local(x, y, z, expression='closed'):
    d = ell(x, y, z, (0, -.642, .456), (.153, .128, .139))
    d = union(d, ell(x, y, z, (0, -.650, .383), (.153, .115, .079)), .027)
    d = union(d, ell(x, y, z, (0, -.613, .235), (.174, .128, .163)), .052)
    d = union(d, ell(np.abs(x), y, z, (.030, -.786, .403), (.045, .039, .037)), .020)
    if expression == 'closed':
        # Raise and reshape the chin to meet the upper muzzle; no open oral cavity.
        d = union(d, ell(x, y, z, (0, -.759, .371), (.047, .032, .020)), .021)
    else:
        d = union(d, ell(x, y, z, (0, -.761, .314), (.054, .040, .021)), .021)
    d = union(d, ell(np.abs(x), y, z, (.072, -.741, .477), (.032, .021, .009)), .017)
    d = union(d, ell(np.abs(x), y, z, (.071, -.743, .434), (.027, .019, .008)), .010)
    if expression == 'open':
        d = np.maximum(d, -mouth_local(x, y, z))
    return np.maximum(d, -eye_local(x, y, z))


def capsule(x, y, z, a, b, ra, rb):
    vx, vy, vz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
    t = np.clip(((x-a[0])*vx+(y-a[1])*vy+(z-a[2])*vz)/(vx*vx+vy*vy+vz*vz), 0, 1)
    r = ra+(rb-ra)*t
    return np.sqrt((x-a[0]-vx*t)**2+(y-a[1]-vy*t)**2+(z-a[2]-vz*t)**2)-r


def body_field(x, y, z, expression='closed'):
    hx, hy, hz = to_head(x, y, z)
    d = head_local(hx, hy, hz, expression)*1.1
    # Rib cage, shoulder girdle, abdomen and pelvis blend into the neck.
    d = union(d, ell(x, y, z, (0, .085, .473), (.184, .324, .193)), .060)
    d = union(d, ell(x, y, z, (0, -.160, .494), (.155, .166, .184)), .045)
    d = union(d, ell(x, y, z, (0, .291, .460), (.155, .175, .177)), .045)
    d = union(d, ell(x, y, z, (0, .389, .445), (.153, .117, .175)), .046)
    xx = np.abs(x)
    # Foreleg: shoulder, elbow, wrist, compact paw.
    d = union(d, capsule(xx,y,z,(.124,-.166,.481),(.117,-.137,.291),.063,.042), .038)
    d = union(d, capsule(xx,y,z,(.117,-.137,.291),(.116,-.203,.075),.041,.029), .027)
    d = union(d, ell(xx,y,z,(.116,-.234,.043),(.050,.070,.035)), .024)
    # Hindleg: thigh slopes forward to the stifle, hock bends rearward.
    d = union(d, capsule(xx,y,z,(.136,.380,.442),(.151,.323,.279),.088,.052), .040)
    d = union(d, capsule(xx,y,z,(.151,.323,.279),(.149,.521,.127),.051,.034), .028)
    d = union(d, capsule(xx,y,z,(.149,.521,.127),(.149,.509,.057),.031,.027), .021)
    d = union(d, ell(xx,y,z,(.149,.479,.038),(.048,.066,.030)), .019)
    # Small overlapping toe volumes introduce a soft scalloped toe line.
    for center_x, center_y in [(.116,-.260),(.149,.457)]:
        for dx in [-.029,-.010,.010,.029]:
            d=union(d,ell(xx,y,z,(center_x+dx,center_y-.020,.032),(.014,.027,.023)),.008)
    return np.maximum(d, .011-z)


def nose_field(x, y, z):
    # Smaller and slightly lower nose, retaining the sculpted nostril recesses.
    hx=x/(1.10*.93)
    hy=(y-.40)/1.20
    nose_center=.435*1.1+.2426-.0115
    hz=(z-nose_center)/(.83*1.1)+.435
    return old_nose(hx,hy,hz)


LANDMARKS = {
    'eye_R': (EYE_LOCAL*HEAD_SCALE+HEAD_OFFSET).tolist(),
    'eye_L': (EYE_LOCAL*np.array([-1,1,1])*HEAD_SCALE+HEAD_OFFSET).tolist(),
    'nose_center': [0,-.5876,.7096],
    'fore_paw_R': [.116,-.234,.011], 'fore_paw_L': [-.116,-.234,.011],
    'hind_paw_R': [.149,.479,.011], 'hind_paw_L': [-.149,.479,.011],
    'estimated_withers': [0,-.160,.678],
    'estimated_fore_elbow_R': [.117,-.137,.291],
    'estimated_hind_stifle_R': [.151,.323,.279],
    'estimated_hock_R': [.149,.521,.127],
    'tail_root': [0,.420,.590],
}
