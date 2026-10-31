"""Refine the trouser contour at knee height and compute shared morph tracks."""
import math
from svgpathtools import parse_path,Line,Path,CubicBezier,QuadraticBezier
from motion import SAMPLES

PROPS=['x','y','inRotation','inDistance','outRotation','outDistance']
PROPERTY_KEYS={'x':24,'y':25,'inRotation':84,'inDistance':85,'outRotation':86,'outDistance':87}


def black_garment_paths(svg):
    """Remove the hand silhouettes from the black underlay and isolate pants."""
    original=list(parse_path(svg[0].get('d')))
    left_cuff=list(parse_path(svg[42].get('d')))
    right_cuff=list(parse_path(svg[84].get('d')))
    upper=Path(*original[:6],
        right_cuff[0].reversed(),
        CubicBezier(right_cuff[0].start,complex(268.5,455),complex(271,505),complex(276.227,539.746)),
        CubicBezier(complex(276.227,539.746),complex(235,553),complex(180,559),complex(143.354,552.11)),
        Line(complex(143.354,552.11),complex(110,552.11)),
        CubicBezier(complex(110,552.11),complex(114,515),complex(119,465),left_cuff[1].end),
        left_cuff[1].reversed(),left_cuff[0].reversed(),
        Line(left_cuff[0].start,original[82].start),*original[82:])
    lower=Path(*original[34:55],
        CubicBezier(original[54].end,complex(80.446,563.182),complex(98,535),complex(110,520)),
        Line(complex(110,520),complex(277,520)),
        CubicBezier(complex(277,520),complex(278,534),complex(279,548),original[34].start))
    assert upper.isclosed() and lower.isclosed()
    return upper.d(),lower.d()


def simplify(keys,tolerance):
    """Keep the interpolation error below a subpixel bound at every sample."""
    if len(keys)<3:return keys
    a,b=keys[0],keys[-1]
    errors=[abs(v-(a[1]+(b[1]-a[1])*(f-a[0])/(b[0]-a[0]))) for f,v in keys]
    index=max(range(len(keys)),key=errors.__getitem__)
    if errors[index]<=tolerance:return [a,b]
    return simplify(keys[:index+1],tolerance)[:-1]+simplify(keys[index:],tolerance)


def refine_pants(d):
    original=parse_path(d);segments=[]
    for segment in original:
        cuts=[0,1]
        for y in [560,580,600,620,640,660,680,700,715,725]:
            if min(segment.start.imag,segment.end.imag)<y<max(segment.start.imag,segment.end.imag):
                cuts += [t for t,_ in segment.intersect(Line(complex(-1000,y),complex(2000,y))) if 1e-7<t<1-1e-7]
        cuts=sorted(set(cuts))
        for a,b in zip(cuts,cuts[1:]):
            piece=segment.cropped(a,b)
            # Shorter spans let the nonlinear warp retain smooth tangents.
            count=max(1,math.ceil(abs(piece.end-piece.start)/12)) if max(piece.start.imag,piece.end.imag)>550 else 1
            segments += [piece.cropped(j/count,(j+1)/count) for j in range(count)]
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
        q=warp(p,frame)
        # Transform tangents by the same local derivative on both sides of
        # a vertex. Warping the remote control points independently creates
        # a cusp at an otherwise smooth subdivision vertex.
        epsilon=.001
        dx=(warp(p+epsilon,frame)-warp(p-epsilon,frame))/(2*epsilon)
        dy=(warp(p+epsilon*1j,frame)-warp(p-epsilon*1j,frame))/(2*epsilon)
        def tangent(handle):return dx*handle.real+dy*handle.imag
        a=tangent(incoming-p);b=tangent(outgoing-p)
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
        if max(abs(v-original[prop]) for v in values)>=1e-5:
            tracks[prop]=simplify(list(zip(SAMPLES,values)),.0005 if prop.endswith('Rotation') else .06)
    return tracks
