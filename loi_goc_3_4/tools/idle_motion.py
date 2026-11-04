"""Native idle motion shared by the source builder and OpenRive MCP update."""
import math

IDLE_FRAMES = 1080  # 18 seconds, with a seamless return to neutral.
# Two playful gestures separated by long neutral rests. Each tilt eases in,
# lingers briefly, then settles back; the character does not sway constantly.
HEAD_ANCHORS = [(0, 0), (126, 0), (156, -.3),
                (222, 3.2), (258, 3.2), (330, 0),
                (606, 0), (642, .25), (714, -2.6), (750, -2.6),
                (810, .6), (864, 0), (1080, 0)]
BLINK_STARTS = [186, 468, 690, 1002]


def head_keys():
    """Sample smoothstep easing; portable to the CLI and native runtimes."""
    out = []
    for (a, va), (b, vb) in zip(HEAD_ANCHORS, HEAD_ANCHORS[1:]):
        for frame in range(a, b, 6):
            t = (frame-a)/(b-a)
            out.append((frame, va+(vb-va)*t*t*(3-2*t)))
    return out + [(IDLE_FRAMES, 0)]


def head_radians():
    return [(f, math.radians(v)) for f, v in head_keys()]


def blink_keys():
    out = [(0, 1)]
    for frame in BLINK_STARTS:
        out += [(frame, 1), (frame+5, .04), (frame+7, .04), (frame+15, 1)]
    return out + [(IDLE_FRAMES, 1)]
