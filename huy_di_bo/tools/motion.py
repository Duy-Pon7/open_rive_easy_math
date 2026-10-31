"""Huy-specific continuous arm and two-segment leg deformation."""
import math
from functools import lru_cache

FRAMES=72
FPS=60
SAMPLES=range(0,FRAMES+1,2)
LEG_BIND={'left':(complex(82,510),complex(77,665)),
          'right':(complex(185,510),complex(180,658))}
THIGH_LENGTH=84
SHIN_LENGTH=84

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

@lru_cache(maxsize=1024)
def gait(frame):
    t=2*math.pi*frame/FRAMES
    bob=-1.8*(1-math.cos(2*t))
    left=max(0,-math.sin(t))**2;right=max(0,math.sin(t))**2
    return dict(bob=bob,left_x=6*math.cos(t),right_x=-6*math.cos(t),
                left_y=-24*left-bob,right_y=-24*right-bob,
                left_arm=math.radians(3*math.cos(t)),right_arm=math.radians(-3*math.cos(t)),
                head=.45*math.sin(t))

def knee_position(hip,ankle):
    axis=ankle-hip;distance=min(abs(axis),THIGH_LENGTH+SHIN_LENGTH-1e-5)
    unit=axis/abs(axis)
    along=(THIGH_LENGTH**2-SHIN_LENGTH**2+distance**2)/(2*distance)
    forward=math.sqrt(max(0,THIGH_LENGTH**2-along**2))
    return hip+unit*along+complex(unit.imag,-unit.real)*forward

@lru_cache(maxsize=1024)
def leg_pose(side,frame):
    hip,ankle=LEG_BIND[side];g=gait(frame)
    target=ankle+complex(g[side+'_x'],g[side+'_y'])
    return hip,knee_position(hip,target),target

def leg_map(point,side,frame):
    hip,ankle=LEG_BIND[side];knee=knee_position(hip,ankle)
    h,k,a=leg_pose(side,frame)
    thigh=h+(point-hip)*(k-h)/(knee-hip)
    shin=k+(point-knee)*(a-k)/(ankle-knee)
    lower=smooth((point.imag-knee.imag+14)/28)
    bent=thigh*(1-lower)+shin*lower
    cuff=smooth((point.imag-625)/25)
    bent=bent*(1-cuff)+(point+a-ankle)*cuff
    return point+(bent-point)*smooth((point.imag-510)/40)

def pants(point,frame):
    # Loose shorts follow the leg cuffs, with a fixed waistband. Applying
    # the two-bone IK map to their broad outline used to pinch the hips and
    # fold the crotch. This bounded shear keeps the fabric contour ordered.
    t=max(0,min(1,(point.imag-490)/150))
    falloff=t*t*t*(t*(6*t-15)+10)
    right=smooth((point.real-122)/32)
    g=gait(frame)
    shift=complex(g['left_x']*(1-right)+g['right_x']*right,
                  g['left_y']*(1-right)+g['right_y']*right)
    return point+shift*falloff

def arms(point,frame):
    x,y=point.real,point.imag;g=gait(frame);result=point
    for pivot,angle,weight in [
        (complex(80,280),g['left_arm'],smooth((90-x)/32)*smooth((y-290)/90)),
        (complex(193,280),g['right_arm'],smooth((x-192)/30)*smooth((y-290)/90))]:
        rotated=pivot+(point-pivot)*complex(math.cos(angle),math.sin(angle))
        result+=(rotated-point)*weight*(1-smooth((y-519)/20))
    return result

def body(point,frame):
    # The trousers now have their own contour; arm motion cannot pull them.
    return arms(point,frame)

def node_tracks():
    base={('CharacterRoot','x'):133,('CharacterRoot','y'):510,
          ('LeftFoot','x'):77,('LeftFoot','y'):665,
          ('RightFoot','x'):180,('RightFoot','y'):658,
          ('Head','rotationDegrees'):0}
    for side,(hip,ankle) in LEG_BIND.items():
        for joint,point in [('Hip',hip),('Knee',knee_position(hip,ankle)),('Ankle',ankle)]:
            base[side.title()+joint+'Joint','x']=point.real
            base[side.title()+joint+'Joint','y']=point.imag
    tracks={key:[] for key in base}
    for f in range(FRAMES+1):
        g=gait(f)
        values=[133,510+g['bob'],77+g['left_x'],665+g['left_y'],
                180+g['right_x'],658+g['right_y'],g['head']]
        for side in LEG_BIND:
            for point in leg_pose(side,f):values += [point.real,point.imag]
        for key,value in zip(base,values):tracks[key].append(value)
    return base,tracks
