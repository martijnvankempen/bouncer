class Input:
    """One frame of fighter input: move from -1 (back) to 1 (forward), plus button presses."""

    def __init__(self, move=0.0, jump=False, punch=False, hold=False, special=False):
        self.move = move
        self.jump = jump
        self.punch = punch
        self.hold = hold
        self.special = special


def read():
    """The badge's buttons and touch pad: badge.held/pressed already merge both."""
    move = 0.0
    if badge.held(BUTTON_LEFT):
        move -= 1.0
    if badge.held(BUTTON_RIGHT):
        move += 1.0
    return Input(
        move,
        badge.pressed(BUTTON_UP),
        badge.pressed(BUTTON_SELECT),
        badge.held(BUTTON_SELECT),
        badge.pressed(BUTTON_DOWN),
    )


NONE = Input()
