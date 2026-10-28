"""Shared gentle index-finger motion, measured in artboard pixels."""
BASE_Y = -90
HEIGHT = 252
PRESS_DEPTH = 14
RELEASE_LIFT = 2
RELEASE_APEX_FRAME = 26
DURATION = 36

def ease(t):
    # Zero velocity and acceleration at each end, avoiding a mechanical stop.
    return t*t*t*(t*(t*6-15)+10)

def release_offset(frame):
    if frame <= RELEASE_APEX_FRAME:
        return PRESS_DEPTH-(PRESS_DEPTH+RELEASE_LIFT)*ease(frame/RELEASE_APEX_FRAME)
    return -RELEASE_LIFT+RELEASE_LIFT*ease((frame-RELEASE_APEX_FRAME)/(DURATION-RELEASE_APEX_FRAME))

PROFILES = {
    'idle': [(0,0),(1,0)],
    'press_down': [(f,PRESS_DEPTH*ease(f/DURATION)) for f in range(DURATION+1)],
    'hold': [(0,PRESS_DEPTH),(60,PRESS_DEPTH)],
    'release_up': [(f,release_offset(f)) for f in range(DURATION+1)],
}
