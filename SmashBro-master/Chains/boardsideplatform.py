import melee
import random
from Chains.chain import Chain
from melee.enums import Action, Button

class BoardSidePlatform(Chain):
    def __init__(self, right_platform, attack=True):
        self.right_platform = right_platform
        self.interruptible = True
        self.attack = attack

    def step(self, gamestate, smashbro_state, opponent_state):
        if self.logger:
            self.logger.log("Notes", " right side platform: " + str(self.right_platform) + " ", concat=True)

        platform_center = 0
        platform_height, platform_left, platform_right = melee.side_platform_position(self.right_platform, gamestate.stage)
        plat_exist = platform_height is not None
        if platform_height is not None:
            platform_center = (platform_left + platform_right) / 2

        top_platform_height, _, _ = melee.top_platform_position(gamestate.stage)

        # y height for bf side plat was 27.2
        # 0 degree wavedash involved airdodge sideways at 22.6 (from 4.2 units below)

        # TODO fix for FOD
        # Where to dash dance to
        pivot_point = platform_center
        # If opponent is on the platform, get right under them
        if platform_left < opponent_state.position.x < platform_right:
            pivot_point = opponent_state.position.x

        # Unless we don't need to attack them, then it's safe to just board asap
        if not self.attack and (platform_left+2 < smashbro_state.position.x < platform_right-2):
            pivot_point = smashbro_state.position.x

        # If we're just using the side platform as a springboard, then go closer in than the middle
        if top_platform_height is not None and (opponent_state.position.y >= top_platform_height):
            if smashbro_state.position.x > 0:
                pivot_point = platform_left + 8
            else:
                pivot_point = platform_right - 8

        # Don't run off the stage (mostly on Yoshis)
        pivot_point = max(-melee.stages.EDGE_GROUND_POSITION[gamestate.stage]+5, pivot_point)
        pivot_point = min(melee.stages.EDGE_GROUND_POSITION[gamestate.stage]-5, pivot_point)

        if smashbro_state.on_ground:
            self.interruptible = True
            # If we're already on the platform, just do nothing. We shouldn't be here
            if smashbro_state.position.y > 5:
                self.controller.release_all()
                return

        # Are we in position to jump?
        if (abs(smashbro_state.position.x - pivot_point) < 5) and (platform_left+2 < smashbro_state.position.x < platform_right-2):
            # Do pivot jumps to prevent too much unpredictable horizontal movement
            if smashbro_state.action == Action.TURNING:
                self.interruptible = False
                self.controller.press_button(melee.Button.BUTTON_Y)
                return

        # If we're crouching, keep holding Y
        if smashbro_state.action == Action.KNEE_BEND:
            # Jump toward the pivot point, if we're far away
            if abs(smashbro_state.position.x - pivot_point) > 10:
                self.controller.tilt_analog(melee.Button.BUTTON_MAIN, int(smashbro_state.position.x < pivot_point), 0)
            else:
                self.controller.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0.5)

            self.controller.press_button(melee.Button.BUTTON_Y)
            self.interruptible = False
            return

        # Waveland down
        aerials = [Action.NAIR, Action.FAIR, Action.UAIR, Action.BAIR, Action.DAIR]
        if smashbro_state.ecb.bottom.y + smashbro_state.position.y > platform_height and smashbro_state.action not in aerials:
            self.interruptible = True
            self.controller.press_button(melee.Button.BUTTON_L)
            # When we're choosing to not attack, just get close to the opponent if we're already
            x = int(smashbro_state.position.x < opponent_state.position.x) * 0.8
            if not self.attack and abs(smashbro_state.position.x - opponent_state.position.x) < 10:
                x = 0.5
            self.controller.tilt_analog(melee.Button.BUTTON_MAIN, x, 0)
            return

        # Don't jump into Peach's dsmash or SH early dair spam
        dsmashactive = opponent_state.action == Action.DOWNSMASH and opponent_state.action_frame <= 22
        if (opponent_state.action == Action.DAIR or dsmashactive) and gamestate.distance < 13:
            self.interruptible = True
            self.controller.press_button(melee.Button.BUTTON_L)
            self.controller.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0)
            return

        # Does not look for KNEE_BEND because smashbro needs to discern between SH and FH
        y_afternineframes = opponent_state.position.y
        gravity = self.framedata.characterdata[opponent_state.character]["Gravity"]
        y_speed = opponent_state.speed_y_self
        for i in range(1,10):
            y_afternineframes += y_speed
            y_speed -= gravity

        # Last resort, just dash at the center of the platform
        if smashbro_state.on_ground:
            self.interruptible = True
            #If we're starting the turn around animation, keep pressing that way or
            #   else we'll get stuck in the slow turnaround
            if smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
                return

            #Dash back, since we're about to start running
            if smashbro_state.action == Action.DASHING and smashbro_state.action_frame >= 11:
                self.controller.tilt_analog(melee.Button.BUTTON_MAIN, int(not smashbro_state.facing), .5)
                return
            else:
                self.controller.tilt_analog(melee.Button.BUTTON_MAIN, int(smashbro_state.position.x < pivot_point), .5)
                return
        # Mash analog L presses to L-cancel if smashbro is throwing out an aerial
        elif not smashbro_state.on_ground and smashbro_state.action in aerials:
            self.interruptible = False
            if gamestate.frame % 2 == 0:
                self.controller.press_shoulder(Button.BUTTON_L, 1)
            else:
                self.controller.press_shoulder(Button.BUTTON_L, 0)
            return
        else:
            self.controller.empty_input()
