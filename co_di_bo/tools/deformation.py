"""Refine the trouser contour at knee height and compute shared morph tracks."""
import math
from svgpathtools import parse_path,Line,Path,CubicBezier,QuadraticBezier
from motion import SAMPLES

PROPS=['x','y','inRotation','inDistance','outRotation','outDistance']
PROPERTY_KEYS={'x':24,'y':25,'inRotation':84,'inDistance':85,'outRotation':86,'outDistance':87}


def refine_pants(d):
    original=parse_path(d);segments=[]
    for segment in original:
        cuts=[0,1]
        for y in [570,600,620,635,650,665,680,700,715,730]:
            if min(segment.start.imag,segment.end.imag)<y<max(segment.start.imag,segment.end.imag):
                cuts += [t for t,_ in segment.intersect(Line(complex(-1000,y),complex(2000,y))) if 1e-7<t<1-1e-7]
        cuts=sorted(set(cuts))
        segments += [segment.cropped(a,b) for a,b in zip(cuts,cuts[1:])]
    # Cropping cubic segments can introduce sub-ulp endpoint discrepancies.
    # Snap shared endpoints so the Rive contour remains one closed path.
    joined=[]
    for i,segment in enumerate(segments):
        start=joined[-1].end if joined else original[0].start
        end=original[0].start if i==len(segments)-1 else segment.end
        if isinstance(segment,CubicBezier):segment=CubicBezier(start,segment.control1,segment.control2,end)
        elif isinstance(segment,QuadraticBezier):segment=QuadraticBezier(start,segment.control,end)
        else:segment=Line(start,end)
        joined.append(segment)
    refined=Path(*joined)
    assert refined.isclosed() and len(refined.continuous_subpaths())==1
    return refined.d()


def vertex_tracks(original,warp):
    p=complex(original['x'],original['y'])
    incoming=p+original['inDistance']*complex(math.cos(original['inRotation']),math.sin(original['inRotation']))
    outgoing=p+original['outDistance']*complex(math.cos(original['outRotation']),math.sin(original['outRotation']))
    poses=[]
    for frame in SAMPLES:
        q=warp(p,frame);a=warp(incoming,frame)-q;b=warp(outgoing,frame)-q
        poses.append(dict(x=q.real,y=q.imag,inRotation=math.atan2(a.imag,a.real),inDistance=abs(a),
                          outRotation=math.atan2(b.imag,b.real),outDistance=abs(b)))
    tracks={}
    for prop in PROPS:
        values=[pose[prop] for pose in poses]
        if prop.endswith('Rotation'):
            previous=original[prop]
            for i,value in enumerate(values):
                while value-previous>math.pi:value-=2*math.pi
                while value-previous<-math.pi:value+=2*math.pi
                values[i]=value;previous=value
        if max(abs(v-original[prop]) for v in values)>=1e-5:tracks[prop]=list(zip(SAMPLES,values))
    return tracks
