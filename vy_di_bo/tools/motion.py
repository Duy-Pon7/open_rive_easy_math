"""Vy: continuous exposed legs, alternating planted sandals and skirt sway."""
import math
from functools import lru_cache

FRAMES=72
SAMPLES=range(0,FRAMES+1,2)
LEG_BIND={'left':(complex(200,665),complex(197,747)),
          'right':(complex(280,665),complex(281,735))}
LEG_LENGTHS={'left':(44,44),'right':(38,38)}

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

@lru_cache(maxsize=1024)
def gait(frame):
    t=2*math.pi*frame/FRAMES
    bob=-1.8*(1-math.cos(2*t))
    return dict(bob=bob,left_x=10*math.cos(t),right_x=-10*math.cos(t),
                left_y=-22*max(0,-math.sin(t))**2-bob,
                right_y=-22*max(0,math.sin(t))**2-bob,
                left_arm=math.radians(3*math.cos(t)),
                right_arm=math.radians(-3*math.cos(t)),
                skirt_x=2*math.sin(t),head=.45*math.sin(t))

def knee_position(hip,ankle,side):
    thigh,shin=LEG_LENGTHS[side];axis=ankle-hip;distance=abs(axis)
    assert distance<thigh+shin
    unit=axis/distance
    along=(thigh**2-shin**2+distance**2)/(2*distance)
    forward=math.sqrt(max(0,thigh**2-along**2))
    return hip+unit*along+complex(unit.imag,-unit.real)*forward

@lru_cache(maxsize=1024)
def leg_pose(side,frame):
    hip,ankle=LEG_BIND[side];g=gait(frame)
    shift=complex(g[side+'_x'],g[side+'_y'])
    # Keep the short visible calf and sandal in their original silhouette.
    # The upper attachment slides beneath the skirt, where it is hidden.
    return hip+shift,knee_position(hip,ankle,side)+shift,ankle+shift

def leg_map(point,side,frame):
    g=gait(frame)
    return point+complex(g[side+'_x'],g[side+'_y'])

def left_leg(point,frame):return leg_map(point,'left',frame)
def right_leg(point,frame):return leg_map(point,'right',frame)

def arms(point,frame):
    x,y=point.real,point.imag;g=gait(frame);result=point
    for pivot,angle,weight in [
        (complex(182,306),g['left_arm'],smooth((214-x)/38)*smooth((y-300)/80)),
        (complex(319,305),g['right_arm'],smooth((x-314)/30)*smooth((y-300)/80))]:
        rotated=pivot+(point-pivot)*complex(math.cos(angle),math.sin(angle))
        result+=(rotated-point)*weight*(1-smooth((y-545)/16))
    return result

def body(point,frame):
    p=arms(point,frame)
    return p+complex(gait(frame)['skirt_x']*smooth((p.imag-535)/125),0)


def skirt(point,frame):
    return point+complex(gait(frame)['skirt_x']*smooth((point.imag-535)/125),0)

def node_tracks():
    base={('CharacterRoot','x'):245,('CharacterRoot','y'):500,
          ('Head','rotationDegrees'):0}
    for side,(hip,ankle) in LEG_BIND.items():
        for joint,point in [('Hip',hip),('Knee',knee_position(hip,ankle,side)),('Ankle',ankle)]:
            base[side.title()+joint+'Joint','x']=point.real
            base[side.title()+joint+'Joint','y']=point.imag
    tracks={key:[] for key in base}
    for f in range(FRAMES+1):
        g=gait(f);values=[245,500+g['bob'],g['head']]
        for side in LEG_BIND:
            for point in leg_pose(side,f):values += [point.real,point.imag]
        for key,value in zip(base,values):tracks[key].append(value)
    return base,tracks
