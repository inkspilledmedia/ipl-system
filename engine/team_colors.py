"""Per-team color profiles, calibrated from the six reference HEAD TO HEAD
renders. Each entry has two fields:

    background  RGB tuple — the team's brand color, used as recolor target
                for the diagonal stripes and player cards
    win_digit   RGB tuple — color of the WIN ## stat number, sampled from
                the actual digit pixels in the references

Background colors are bright/saturated brand values. The HSV recolor pass
preserves each original pixel's saturation/value, so passing a vivid target
keeps the stripe gradients looking natural.

Digit colors were sampled from the WIN ## pixel regions in the references.
GT, KKR, RR, SRH all use team-specific digit colors (not gold).
"""

TEAM_COLORS: dict[str, dict] = {
    "RCB":  {"background": (180,  20,  25), "win_digit": (229, 183,  66)},
    "CSK":  {"background": (250, 200,   0), "win_digit": (249, 220,   0)},
    "MI":   {"background": ( 30,  90, 200), "win_digit": (254, 204,  47)},
    "RR":   {"background": (220,  40, 120), "win_digit": (255,   0, 109)},
    "KKR":  {"background": ( 75,  35, 130), "win_digit": (163,  99, 255)},
    "SRH":  {"background": (235, 100,   0), "win_digit": (238, 101,   0)},
    "GT":   {"background": ( 20,  30,  55), "win_digit": (109, 133, 207)},
    "LSG":  {"background": ( 25,  55, 130), "win_digit": (229, 183,  66)},
    "DC":   {"background": (165,  30,  30), "win_digit": (229, 183,  67)},
    "PBKS": {"background": (210,  25,  40), "win_digit": (253, 223, 175)},
}


def get_team_colors(team: str) -> dict | None:
    return TEAM_COLORS.get(team.upper())
