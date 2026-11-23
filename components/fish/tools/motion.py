"""Periodic swimming profiles, sampled at 60 fps with a seamless 2 s loop."""
import math

FRAMES = 120
BASE = {
    ('FishRoot','x'):900, ('FishRoot','y'):500,
    ('FishRoot','rotationDegrees'):0,
    ('Tail','x'):600,
    ('Tail','rotationDegrees'):0, ('Tail','scaleX'):1, ('Tail','scaleY'):1,
    ('DorsalFin','y'):298, ('DorsalFin','rotationDegrees'):0, ('DorsalFin','scaleX'):1,
    ('VentralFin','y'):727, ('VentralFin','rotationDegrees'):0, ('VentralFin','scaleX'):1, ('VentralFin','scaleY'):1,
    ('PectoralFin','rotationDegrees'):0, ('PectoralFin','scaleX'):1, ('PectoralFin','scaleY'):1,
}


def tracks():
    out={k:[] for k in BASE}
    for f in range(FRAMES+1):
        t=2*math.pi*f/FRAMES
        # Inset the tail root under the body while it flaps so its angled
        # outline stays covered at the attachment; idle retains the exact SVG.
        values=[900+4*math.sin(t),500+5*math.sin(t),.3*math.sin(t),614,
                4.5*math.sin(2*t),1-.16*math.sin(2*t)**2,1+.018*math.sin(2*t),
                310,.8*math.sin(2*t-.7),1-.025*math.sin(2*t)**2,
                707,3*math.sin(2*t+.8),1-.05*math.sin(2*t)**2,1-.04*math.sin(2*t)**2,
                8*math.sin(4*t-.8),.84+.16*math.cos(4*t),.97+.03*math.cos(4*t)]
        for key,value in zip(BASE,values):out[key].append(value)
    return out
