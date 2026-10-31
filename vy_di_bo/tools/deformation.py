"""Refine the trouser contour at knee height and compute shared morph tracks."""
import math
from svgpathtools import parse_path,Line,Path,CubicBezier,QuadraticBezier
from motion import SAMPLES

PROPS=['x','y','inRotation','inDistance','outRotation','outDistance']
PROPERTY_KEYS={'x':24,'y':25,'inRotation':84,'inDistance':85,'outRotation':86,'outDistance':87}


def garment_path(svg,index):
    """Separate the jacket hem, hands and skirt hidden in the SVG underlay."""
    if index in [36,45]:
        leg=list(parse_path(svg[index].get('d')))
        top=leg[0]
        # Keep overlap with the moving skirt even when the foot is planted.
        # Only this concealed extension changes the original leg silhouette.
        return Path(Line(top.start,top.start-35j),Line(top.start-35j,top.end-35j),
            Line(top.end-35j,top.end),*leg[1:]).d()
    if index not in [0,1]:return svg[index].get('d')
    outer=list(parse_path(svg[0].get('d')))
    lower=list(parse_path(svg[1].get('d')))
    if index==0:
        return Path(*outer[:12],Line(outer[11].end,lower[40].end),
            *[s.reversed() for s in lower[24:41][::-1]],
            Line(lower[24].start,outer[35].start),*outer[35:]).d()
    # The sides continue behind the cuffs into a concealed waistband.
    # There are no hand-shaped bumps or arm-driven vertices on the skirt.
    return Path(*lower[6:19],
        CubicBezier(lower[18].end,complex(151,525),complex(157,495),complex(163,476)),
        Line(complex(163,476),complex(163,430)),
        Line(complex(163,430),complex(336,430)),
        Line(complex(336,430),complex(336,476)),
        CubicBezier(complex(336,476),complex(340,494),complex(342,513),lower[6].start)).d()


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
        for y in [535,560,600,640,665,680,695,710,725,740,750]:
            if min(segment.start.imag,segment.end.imag)<y<max(segment.start.imag,segment.end.imag):
                cuts += [t for t,_ in segment.intersect(Line(complex(-1000,y),complex(2000,y))) if 1e-7<t<1-1e-7]
        cuts=sorted(set(cuts))
        for a,b in zip(cuts,cuts[1:]):
            piece=segment.cropped(a,b)
            # Shorter spans let the nonlinear warp retain smooth tangents.
            count=max(1,math.ceil(abs(piece.end-piece.start)/12)) if max(piece.start.imag,piece.end.imag)>530 else 1
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
