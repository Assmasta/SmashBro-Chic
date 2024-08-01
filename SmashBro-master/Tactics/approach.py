import melee
import Chains
import random
from melee.enums import Action, Button, Character
from Tactics.tactic import Tactic
from Tactics.punish import Punish
from Chains.shffl import SHFFL_DIRECTION
from Chains.dshffl import DSHFFL_DIRECTION
from Chains.grabandthrow import THROW_DIRECTION
from Chains.tilt import TILT_DIRECTION
from Chains.smashattack import SMASH_DIRECTION

# TODO zoning, also challenge

# TODO getting under helpless airborne opponents

class Approach(Tactic):
    def __init__(self, logger, controller, framedata, difficulty):
        Tactic.__init__(self, logger, controller, framedata, difficulty)
        self.random_approach = random.randint(0, 100)

    def shouldapproach(smashbro_state, opponent_state, gamestate, framedata, logger):
        if len(gamestate.projectiles) > 0:
            return False
        # Specify that this needs to be platform approach
        framesleft = Punish.framesleft(opponent_state, framedata, smashbro_state)
        if logger:
            logger.log("Notes", " framesleft: " + str(framesleft) + " ", concat=True)
        if framesleft >= 9:
            return True
        return False

    def approach_too_dangerous(smashbro_state, opponent_state, gamestate, framedata):
        # TODO Do we actually care about this projectile?
        if len(gamestate.projectiles) > 0:
            return True
        if framedata.is_attack(opponent_state.character, opponent_state.action):
            return True
        return False

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)
        #If we can't interrupt the chain, just continue it
        if self.chain != None and not self.chain.interruptible:
            self.chain.step(gamestate, smashbro_state, opponent_state)
            return

        # makeshift transform
        if smashbro_state.character == Character.ZELDA and smashbro_state.action in [Action.FALLING, Action.STANDING, Action.TURNING]:
            self.controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0)
            self.controller.press_button(Button.BUTTON_B)
            return

        # mark opponents as light/heavy and fast-faller/floaty
        if opponent_state.character in [Character.FOX, Character.FALCO, Character.PIKACHU, Character.JIGGLYPUFF]:
            light = True
            heavy = False
        else:
            light = False
            heavy = True

        if opponent_state.character in [Character.FOX, Character.FALCO, Character.CPTFALCON]:
            fastfaller = True
            floaty = False
        else:
            fastfaller = False
            floaty = True

        edge = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]

        needswavedash = smashbro_state.action in [Action.LANDING_SPECIAL, Action.SHIELD, Action.SHIELD_START, \
            Action.SHIELD_RELEASE, Action.SHIELD_STUN, Action.SHIELD_REFLECT]
        if needswavedash:
            self.pickchain(Chains.Wavedash, [True])
            return

        # Are we behind in the game?
        losing = smashbro_state.stock < opponent_state.stock or (smashbro_state.stock == opponent_state.stock and smashbro_state.percent > opponent_state.percent)
        opp_top_platform = False
        top_platform_height, top_platform_left, top_platform_right = melee.top_platform_position(gamestate.stage)
        if top_platform_height is not None:
            opp_top_platform = (opponent_state.position.y+1 >= top_platform_height) and (top_platform_left-1 < opponent_state.position.x < top_platform_right+1)

        # If opponent is on a side platform and we're not
        on_main_platform = smashbro_state.position.y < 1 and smashbro_state.on_ground
        if not opp_top_platform:
            if opponent_state.position.y > 10 and opponent_state.on_ground and on_main_platform:
                self.pickchain(Chains.BoardSidePlatform, [opponent_state.position.x > 0])
                return

        teching = opponent_state.action in [Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN, Action.BACKWARD_TECH, Action.TECH_MISS_DOWN,
                 Action.TECH_MISS_UP, Action.NEUTRAL_TECH, Action.GROUND_ROLL_BACKWARD_UP, Action.GROUND_ROLL_BACKWARD_DOWN]

        # Dash dance up to the correct spacing
        dashdanceradius = random.randint(0, 3)
        pivotpoint = opponent_state.position.x
        bufferzone = 30
        if opponent_state.character == Character.FALCO:
            bufferzone = 40
        if opponent_state.character == Character.CPTFALCON:
            bufferzone = 35
        if opponent_state.character == Character.MARTH:
            bufferzone = 40
        if opponent_state.character == Character.SHEIK:
            bufferzone = 38
        if opponent_state.position.x > smashbro_state.position.x:
            bufferzone *= -1

        side_plat_height, side_plat_left, side_plat_right = melee.side_platform_position(opponent_state.position.x > 0,
                                                                                         gamestate.stage)
        on_side_plat = False
        plat_exist = side_plat_height is not None
        if side_plat_height is not None:
            on_side_plat = opponent_state.on_ground and abs(opponent_state.position.y - side_plat_height) < 5

        if on_side_plat:
            bufferzone = 0

        pivotpoint += bufferzone

        # Don't run off the stage though, adjust this back inwards a little if it's off
        edgebuffer = 10
        pivotpoint = min(pivotpoint, edge - edgebuffer)
        pivotpoint = max(pivotpoint, (-edge) + edgebuffer)
        if edge - abs(smashbro_state.position.x) > 15:
            dashdanceradius = 0

        # if opponent is lying or teching on top platform, board it
        if opp_top_platform and opponent_state.action in \
                [Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN, Action.BACKWARD_TECH, Action.TECH_MISS_DOWN,
                 Action.TECH_MISS_UP, Action.NEUTRAL_TECH, Action.GROUND_ROLL_BACKWARD_UP, Action.GROUND_ROLL_BACKWARD_DOWN]:
            self.pickchain(Chains.BoardTopPlatform)
            return

        if top_platform_height is not None:
            if abs(opponent_state.position.x) < 20 and opponent_state.position.y >= top_platform_height + 15:
                self.pickchain(Chains.BoardTopPlatform)
                return

        # If opponent is on top platform. Unless we're ahead. Then let them camp
        if opp_top_platform and losing and random.randint(0, 20) == 0:
            self.pickchain(Chains.BoardTopPlatform)
            return

        # Jump over Samus Bomb
        samus_bomb = opponent_state.character == Character.SAMUS and opponent_state.action == Action.SWORD_DANCE_4_MID
        if samus_bomb and opponent_state.position.y < 5:
            landing_spot = opponent_state.position.x
            if opponent_state.position.x < smashbro_state.position.x:
                landing_spot -= 10
            else:
                landing_spot += 10

            # Don't jump off the stage
            if abs(landing_spot) < melee.stages.EDGE_GROUND_POSITION[gamestate.stage]:
                self.pickchain(Chains.JumpOver, [landing_spot])
                return

        opcrouching = opponent_state.action in [Action.CROUCHING, Action.CROUCH_START, Action.CROUCH_END]
        grounded_actionable = [Action.STANDING, Action.DASHING, Action.RUNNING, Action.TURNING]

        # approach opponent sometimes (50% chance per approach)
        if self.random_approach < 50:
            if not self.framedata.is_attack(opponent_state.character, opponent_state.action):
                # We need to be dashing towards our opponent. Not too close to the ledge (35 > 50)
                diff_x = abs(smashbro_state.position.x - opponent_state.position.x)
                diff_y = abs(smashbro_state.position.y - opponent_state.position.y)
                facing_opponent = smashbro_state.facing == (smashbro_state.position.x < opponent_state.position.x)
                if smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
                    facing_opponent = not facing_opponent
                if fastfaller and smashbro_state.on_ground:
                    if ((opcrouching or "out" not in gamestate.custom["predominant_SDI_direction"]) and
                        gamestate.distance < 4 and opponent_state.percent < 16) \
                            or (opponent_state.percent > 59 and gamestate.distance < 7):
                        self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                        if smashbro_state.action_frame == 1:
                            print('approach dsmash')
                        return
                if smashbro_state.action in grounded_actionable and facing_opponent:
                    if opponent_state.action in grounded_actionable and 10 < gamestate.distance < 23:
                        self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                        if smashbro_state.action_frame == 1:
                            print('approach dthrow')
                        return
                    if gamestate.distance < 20 and opponent_state.percent > 59:
                        if smashbro_state.action in [Action.TURNING, Action.STANDING]:
                            self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                            if smashbro_state.action_frame == 1:
                                print('approach ftilt')
                            return
                        elif smashbro_state.action in [Action.DASHING, Action.RUNNING]:
                            self.pickchain(Chains.DashAttack)
                            if smashbro_state.action_frame == 1:
                                print('approach dash attack')
                            return

        self.chain = None
        self.pickchain(Chains.WaveDance, [pivotpoint, dashdanceradius, False])

