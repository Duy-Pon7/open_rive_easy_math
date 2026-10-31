"""Refine the trouser contour at knee height and compute shared morph tracks."""
import math
from svgpathtools import parse_path,Line,Path,CubicBezier,QuadraticBezier
from motion import SAMPLES

PROPS=['x','y','inRotation','inDistance','outRotation','outDistance']
PROPERTY_KEYS={'x':24,'y':25,'inRotation':84,'inDistance':85,'outRotation':86,'outDistance':87}


def garment_path(d,index,svg):
    """Isolate the blue shirt at its real hem, without hand/pants underlays."""
    if index==0:
        outer=list(parse_path(d));hem=list(parse_path(svg[1].get('d')))
        segments=[*outer[:20],Line(outer[19].end,complex(224.612,456.326)),
                  Line(complex(224.612,456.326),hem[3].end)]
        segments += [hem[j].reversed() for j in [3,2,1,0,44,43,42,41,40,39,38,37]]
        segments += [Line(segments[-1].end,outer[0].start)]
        return Path(*segments).d()
    return d


def shorts_path(svg):
    """Original leg hems/crotch plus smooth hip edges behind the hands."""
    segments=list(parse_path(svg[1].get('d')))
    # Open the inseam into a rounded arch. The original one-pixel tip read
    # as a stuck seam and collapsed further when the legs passed each other.
    crotch=[
        CubicBezier(segments[12].end,complex(150,654),complex(149,650),complex(148,644)),
        CubicBezier(complex(148,644),complex(147,638),complex(144,610),complex(142,602)),
        CubicBezier(complex(142,602),complex(140,594),complex(136,594),complex(134,602)),
        CubicBezier(complex(134,602),complex(132,610),complex(124,644),complex(121,653)),
        CubicBezier(complex(121,653),complex(119,659),complex(117,661),complex(113,662)),
        CubicBezier(complex(113,662),complex(109,663),complex(105,664),segments[20].end),
    ]
    lower=[*segments[5:13],*crotch,*segments[21:30]]
    left,right=lower[-1].end,lower[0].start
    # Continue the original outer-leg tangents into the hidden waistband.
    return Path(*lower,
        CubicBezier(left,left+(left-lower[-1].control2)*3,complex(51,489),complex(54,478)),
        # Extend the hidden waistband behind the shirt's deep front slit.
        Line(complex(54,478),complex(54,430)),
        Line(complex(54,430),complex(219,430)),
        Line(complex(219,430),complex(219,474)),
        CubicBezier(complex(219,474),complex(221,482),right-(lower[0].control1-right)*2,right)).d()


def refine_pants(d):
    original=parse_path(d);segments=[]
    for segment in original:
        cuts=[0,1]
        for y in [490,505,520,540,560,575,590,605,620,635,650]:
            if min(segment.start.imag,segment.end.imag)<y<max(segment.start.imag,segment.end.imag):
                cuts += [t for t,_ in segment.intersect(Line(complex(-1000,y),complex(2000,y))) if 1e-7<t<1-1e-7]
        cuts=sorted(set(cuts))
        for a,b in zip(cuts,cuts[1:]):
            piece=segment.cropped(a,b)
            # Shorter spans let the nonlinear warp retain smooth tangents.
            count=max(1,math.ceil(abs(piece.end-piece.start)/12)) if max(piece.start.imag,piece.end.imag)>475 else 1
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
        if max(abs(v-original[prop]) for v in values)>=1e-5:tracks[prop]=list(zip(SAMPLES,values))
    return tracks
