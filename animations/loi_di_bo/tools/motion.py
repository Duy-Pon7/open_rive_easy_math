"""Loi's continuous sleeves and hip/knee/ankle walk cycle."""
import math
from functools import lru_cache

FRAMES=72
SAMPLES=range(0,FRAMES+1,2)
LEG_BIND={'left':(complex(128,550),complex(123,724)),
          'right':(complex(233,550),complex(232,715))}
THIGH_LENGTH=92
SHIN_LENGTH=92

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

@lru_cache(maxsize=1024)
def gait(frame):
    t=2*math.pi*frame/FRAMES
    bob=-2.2*(1-math.cos(2*t))
    return dict(bob=bob,left_x=12*math.cos(t),right_x=-12*math.cos(t),
                left_y=-28*max(0,-math.sin(t))**2-bob,
                right_y=-28*max(0,math.sin(t))**2-bob,
                left_arm=math.radians(3.5*math.cos(t)),
                right_arm=math.radians(-3.5*math.cos(t)),head=.5*math.sin(t))

def knee_position(hip,ankle):
    axis=ankle-hip;distance=abs(axis);unit=axis/distance
    assert distance<THIGH_LENGTH+SHIN_LENGTH
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
    # Broad fabric follows the joint centerline without rotating its width.
    # This retains the original loose silhouette and avoids folding the cuff.
    if point.imag<=knee.imag:
        delta=(k-knee)*smooth((point.imag-558)/(knee.imag-558))
    else:
        cuff=smooth((point.imag-knee.imag)/(700-knee.imag))
        delta=(k-knee)*(1-cuff)+(a-ankle)*cuff
    return point+delta

def pants(point,frame):
    cuff=smooth((point.imag-655)/48)
    width=60*(1-cuff)+22*cuff
    center=187-5*cuff
    right=smooth((point.real-center+width/2)/width)
    return leg_map(point,'left',frame)*(1-right)+leg_map(point,'right',frame)*right

def arms(point,frame):
    x,y=point.real,point.imag;g=gait(frame);result=point
    for pivot,angle,weight in [
        (complex(112,342),g['left_arm'],smooth((135-x)/35)*smooth((y-340)/80)),
        (complex(254,337),g['right_arm'],smooth((x-252)/30)*smooth((y-335)/80))]:
        rotated=pivot+(point-pivot)*complex(math.cos(angle),math.sin(angle))
        result+=(rotated-point)*weight*(1-smooth((y-565)/16))
    return result

def body(point,frame):
    return pants(arms(point,frame),frame)


def shirt(point,frame):
    # Sleeve attachments keep the arm motion; the lower shirt and hips stay
    # independent of the hands. The fade occurs beneath the patterned cuff.
    return point+(arms(point,frame)-point)*(1-smooth((point.imag-445)/75))

def node_tracks():
    base={('CharacterRoot','x'):180,('CharacterRoot','y'):550,
          ('LeftFoot','x'):123,('LeftFoot','y'):724,
          ('RightFoot','x'):232,('RightFoot','y'):715,
          ('Head','rotationDegrees'):0}
    for side,(hip,ankle) in LEG_BIND.items():
        for joint,point in [('Hip',hip),('Knee',knee_position(hip,ankle)),('Ankle',ankle)]:
            base[side.title()+joint+'Joint','x']=point.real
            base[side.title()+joint+'Joint','y']=point.imag
    tracks={key:[] for key in base}
    for f in range(FRAMES+1):
        g=gait(f)
        values=[180,550+g['bob'],123+g['left_x'],724+g['left_y'],
                232+g['right_x'],715+g['right_y'],g['head']]
        for side in LEG_BIND:
            for point in leg_pose(side,f):values += [point.real,point.imag]
        for key,value in zip(base,values):tracks[key].append(value)
    return base,tracks
