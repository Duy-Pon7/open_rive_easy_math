"""A 1.2 second walk: alternating planted feet and smoothly joined clothing."""
import math
from functools import lru_cache

FRAMES=72
FPS=60
SAMPLES=range(0,FRAMES+1,2)


def smooth(value):
    t=max(0,min(1,value))
    return t*t*(3-2*t)


@lru_cache(maxsize=1024)
def gait(frame):
    t=2*math.pi*frame/FRAMES
    bob=-2.4*(1-math.cos(2*t))
    left_swing=max(0,-math.sin(t))**2
    right_swing=max(0,math.sin(t))**2
    return dict(bob=bob,left_x=16*math.cos(t),right_x=-16*math.cos(t),
                left_y=-28*left_swing-bob,right_y=-28*right_swing-bob,
                left_swing=left_swing,right_swing=right_swing,
                left_arm=math.radians(4*math.cos(t)),right_arm=math.radians(-4*math.cos(t)),
                head=.55*math.sin(t))


LEG_BIND={'left':(complex(205,550),complex(195,750)),
          'right':(complex(296,550),complex(302,747))}
THIGH_LENGTH=104
SHIN_LENGTH=103


def knee_position(hip,ankle):
    axis=ankle-hip
    distance=min(abs(axis),THIGH_LENGTH+SHIN_LENGTH-1e-5)
    unit=axis/abs(axis)
    along=(THIGH_LENGTH**2-SHIN_LENGTH**2+distance**2)/(2*distance)
    forward=math.sqrt(max(0,THIGH_LENGTH**2-along**2))
    return hip+unit*along+complex(unit.imag,-unit.real)*forward


@lru_cache(maxsize=2048)
def leg_pose(side,frame):
    hip,ankle=LEG_BIND[side]
    g=gait(frame)
    target=ankle+complex(g[side+'_x'],g[side+'_y'])
    return hip,knee_position(hip,target),target


def leg_map(point,side,frame):
    hip,ankle=LEG_BIND[side];knee=knee_position(hip,ankle)
    h,k,a=leg_pose(side,frame)
    thigh=h+(point-hip)*(k-h)/(knee-hip)
    shin=k+(point-knee)*(a-k)/(ankle-knee)
    lower=smooth((point.imag-knee.imag+18)/36)
    bent=thigh*(1-lower)+shin*lower
    # The cuff returns to a rigid ankle translation so its shared outline
    # stays joined to the ankle/foot rather than stretching away from it.
    cuff=smooth((point.imag-710)/22)
    bent=bent*(1-cuff)+(point+a-ankle)*cuff
    weight=smooth((point.imag-560)/45)
    return point+(bent-point)*weight


def node_tracks():
    base={('CharacterRoot','x'):244,('CharacterRoot','y'):550,
          ('LeftFoot','x'):195,('LeftFoot','y'):750,
          ('RightFoot','x'):302,('RightFoot','y'):747,
          ('Head','rotationDegrees'):0,('HeadDetails','rotationDegrees'):0}
    for side,(hip,ankle) in LEG_BIND.items():
        for joint,point in [('Hip',hip),('Knee',knee_position(hip,ankle)),('Ankle',ankle)]:
            base[side.title()+joint+'Joint','x']=point.real
            base[side.title()+joint+'Joint','y']=point.imag
    tracks={key:[] for key in base}
    for f in range(FRAMES+1):
        g=gait(f)
        values=[244,550+g['bob'],195+g['left_x'],750+g['left_y'],
                302+g['right_x'],747+g['right_y'],g['head'],g['head']]
        for side in LEG_BIND:
            for point in leg_pose(side,f):values += [point.real,point.imag]
        for key,value in zip(base,values):tracks[key].append(value)
    return base,tracks


def arms(point,frame):
    x,y=point.real,point.imag
    g=gait(frame)
    result=point
    for pivot,angle,weight in [
        (complex(176,353),g['left_arm'],smooth((195-x)/34)*smooth((y-350)/75)),
        (complex(310,353),g['right_arm'],smooth((x-304)/32)*smooth((y-350)/75))]:
        rotated=pivot+(point-pivot)*complex(math.cos(angle),math.sin(angle))
        result+=(rotated-point)*weight
    return result


def pants(point,frame):
    right=smooth((point.real-249)/16)
    return leg_map(point,'left',frame)*(1-right)+leg_map(point,'right',frame)*right
