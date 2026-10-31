"""Shared gentle index-finger motion, measured in artboard pixels."""
BASE_Y = -73
HEIGHT = 269
PRESS_DEPTH = 14
RELEASE_LIFT = 2
RELEASE_APEX_FRAME = 26
DURATION = 36
CONTACT_FRAME = 36
PRESS_END_FRAME = 60
PULSE_FRAME = 48

def ease(t):
    # Zero velocity and acceleration at each end, avoiding a mechanical stop.
    return t*t*t*(t*(t*6-15)+10)

def release_offset(frame):
    if frame <= RELEASE_APEX_FRAME:
        return PRESS_DEPTH-(PRESS_DEPTH+RELEASE_LIFT)*ease(frame/RELEASE_APEX_FRAME)
    return -RELEASE_LIFT+RELEASE_LIFT*ease((frame-RELEASE_APEX_FRAME)/(DURATION-RELEASE_APEX_FRAME))

PROFILES = {
    'idle': [(0,0),(1,0)],
    # Reach contact in 0.6 s, then keep the finger down during the 0.4 s pulse.
    'press_down': [(f,PRESS_DEPTH*ease(min(1,f/CONTACT_FRAME))) for f in range(PRESS_END_FRAME+1)],
    'hold': [(0,PRESS_DEPTH),(60,PRESS_DEPTH)],
    'release_up': [(f,release_offset(f)) for f in range(DURATION+1)],
}

TOUCH_X = 113.5
# Center the feedback on the rounded finger pad after its 14 px press, rather
# than on the upper edge of the fingertip.
TOUCH_Y = BASE_Y+121.5

PALETTE = [('Blue','#0EA5E9'),('Yellow','#FAC965'),('Pink','#EC4899')]

def feedback(frame,name,part):
    """Return (scale, opacity). Two circles pulse, then only the small one remains."""
    if name=='idle':return .001,0
    if name=='hold':return (.82,1) if part=='inner' else (.001,0)
    if name=='release_up':
        fade=1-ease(min(1,frame/22))
        return (max(.001,.82*fade),fade) if part=='inner' else (.001,0)
    if frame<=CONTACT_FRAME:return .001,0
    after_contact=frame-CONTACT_FRAME
    appear=ease(min(1,after_contact/6))
    expand=ease(min(1,after_contact/12))
    settle=ease(max(0,min(1,(after_contact-12)/12)))
    if part=='inner':return max(.001,expand-.18*settle),appear
    return .1+.9*expand-.4*settle,.32*appear*(1-settle)
