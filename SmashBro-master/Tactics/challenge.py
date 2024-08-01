import melee
import Chains
import random
from melee.enums import Action, Character, Stage
from Tactics.tactic import Tactic
from Tactics.punish import Punish
from Chains.smashattack import SMASH_DIRECTION
from Chains.shffl import SHFFL_DIRECTION
from Chains.dshffl import DSHFFL_DIRECTION
from Chains.tilt import TILT_DIRECTION
from Chains.airattack import AirAttack, AIR_ATTACK_DIRECTION
from Chains.aerial import Aerial, AERIAL_DIRECTION
from Chains.grabandthrow import THROW_DIRECTION
from Chains.fallingaerial import FallingAerial, FALLING_AERIAL_DIRECTION

class Challenge(Tactic):
    """Challenge is for instances where the opponent is not in hitstun, but can be hit

    But Punish won't work here, since opponent is not in a lag state
    """
    def __init__(self, logger, controller, framedata, difficulty):
        Tactic.__init__(self, logger, controller, framedata, difficulty)
        self.keep_running = False

    def canchallenge(smashbro_state, opponent_state, gamestate, framedata, difficulty):
        if opponent_state.invulnerability_left > 0:
            return False

        if smashbro_state.off_stage:
            return False

        if gamestate.distance > 30:
            return False

        # challenge the jumpless
        if opponent_state.jumps_left == 0:
            return True

        # positional arguments:
        # op above
        if smashbro_state.position.y < opponent_state.position.y:
            return True

        # falling on op
        if smashbro_state.speed_y_self < 0 and smashbro_state.position.y > opponent_state.position.y:
            return True

        # hit on the cooldowns
        attackstate = framedata.attack_state(opponent_state.character, opponent_state.action,
                                             opponent_state.action_frame)
        frame = framedata.iasa(opponent_state.character, opponent_state.action)
        if attackstate == melee.enums.AttackState.COOLDOWN and max(0, frame - opponent_state.action_frame) > 4:
            return True

        if opponent_state.action in [Action.DEAD_FALL]:
            return True

        # hit on landings
        if opponent_state.action in [Action.LANDING, Action.LANDING_SPECIAL, Action.NAIR_LANDING, Action.FAIR_LANDING,
                                     Action.BAIR_LANDING, Action. UAIR_LANDING, Action.DAIR_LANDING]:
            return True

        # Opponent must be shielding
        shieldactions = [Action.SHIELD_START, Action.SHIELD, \
                         Action.SHIELD_STUN, Action.SHIELD_REFLECT]
        shielding = opponent_state.action in shieldactions
        if shielding:
            return False

        # Rapid jabs
        if opponent_state.action == Action.LOOPING_ATTACK_MIDDLE:
            return True
        if opponent_state.character == Character.PIKACHU and opponent_state.action == Action.NEUTRAL_ATTACK_1:
            return True
        if opponent_state.character == Character.MARTH and opponent_state.action in [Action.NEUTRAL_ATTACK_1, Action.NEUTRAL_ATTACK_2]:
            return True

        # laser taken
        if gamestate.custom["laser_taken"]:
            return True

        # proximity
        if gamestate.distance < 20 and not smashbro_state.off_stage:
            return True

        return False

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        # If we can't interrupt the chain, just continue it
        if self.chain != None and not self.chain.interruptible:
            self.chain.step(gamestate, smashbro_state, opponent_state)
            return

        # If we chose to run, keep running
        if type(self.chain) == Chains.Run and self.keep_running:
            self.pickchain(Chains.Run, [opponent_state.position.x > smashbro_state.position.x])
            return

        edge = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        grounded_actionable = smashbro_state.action in [Action.STANDING, Action.DASHING, Action.RUNNING, Action.TURNING,
                                                        Action.EDGE_TEETERING_START, Action.EDGE_TEETERING]
        diff_x = abs(smashbro_state.position.x - opponent_state.position.x)
        diff_y = abs(smashbro_state.position.y - opponent_state.position.y)

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

        DI_up = "up" in gamestate.custom["predominant_SDI_direction"]
        DI_down = "down" in gamestate.custom["predominant_SDI_direction"]
        DI_in = "in" in gamestate.custom["predominant_SDI_direction"]
        DI_out = "out" in gamestate.custom["predominant_SDI_direction"]

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

        side_plat_height, side_plat_left, side_plat_right = melee.side_platform_position(opponent_state.position.x > 0, gamestate.stage)
        on_side_plat = False
        plat_exist = side_plat_height is not None
        if side_plat_height is not None:
            on_side_plat = opponent_state.on_ground and abs(opponent_state.position.y - side_plat_height) < 5

        if on_side_plat:
            bufferzone = 0

        # Falling spacies
        chaingrabbable_spacie = False
        if opponent_state.character in [Character.FOX, Character.FALCO]:
            if not opponent_state.on_ground and opponent_state.speed_y_self < 0:
                bufferzone = 30
                chaingrabbable_spacie = True

        pivotpoint += bufferzone

        # Don't run off the stage though, adjust this back inwards a little if it's off
        edgebuffer = 10
        pivotpoint = min(pivotpoint, edge - edgebuffer)
        pivotpoint = max(pivotpoint, (-edge) + edgebuffer)
        if edge - abs(smashbro_state.position.x) > 15:
            dashdanceradius = 0

        if self.logger:
            self.logger.log("Notes", "pivotpoint: " + str(pivotpoint) + " ", concat=True)

        smash_now = opponent_state.action_frame < 6
        if opponent_state.character == Character.CPTFALCON:
            smash_now = opponent_state.action_frame in [4, 12, 20, 27]
        if opponent_state.character == Character.MARTH:
            smash_now = opponent_state.action_frame < 6

        teching = opponent_state.action in [Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN, Action.BACKWARD_TECH,
                                            Action.TECH_MISS_DOWN,
                                            Action.TECH_MISS_UP, Action.NEUTRAL_TECH, Action.GROUND_ROLL_BACKWARD_UP,
                                            Action.GROUND_ROLL_BACKWARD_DOWN]
        crouching = [Action.CROUCHING, Action.CROUCH_START, Action.CROUCH_END]

        relative_y = opponent_state.position.y - smashbro_state.position.y
        edgedistance = melee.stages.EDGE_GROUND_POSITION[gamestate.stage] - abs(smashbro_state.position.x)

        # opponent position
        opponentxvelocity = (opponent_state.speed_air_x_self + opponent_state.speed_ground_x_self + opponent_state.speed_x_attack)
        opponentyvelocity = (opponent_state.speed_y_attack + opponent_state.speed_y_self)
        opponentonright = opponent_state.position.x > smashbro_state.position.x

        approaching = (opponentxvelocity < 0) == opponentonright
        drifting_away = (opponentxvelocity > 0) == opponentonright
        facingop = smashbro_state.facing == opponentonright
        if smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
            facingop = not facingop
        opoutside = abs(smashbro_state.position.x) < abs(opponent_state.position.x)

        in_grab_range = 0 < diff_x < 35
        grabbable = not teching and (in_grab_range and facingop) and \
                    (13 < relative_y < 25 or opponent_state.action == Action.STANDING)
        landing = [Action.LANDING, Action.LANDING_SPECIAL, Action.NAIR_LANDING, Action.FAIR_LANDING,
                                     Action.BAIR_LANDING, Action. UAIR_LANDING, Action.DAIR_LANDING]

        actionexclude = [Action.TURNING_RUN]

        laser_taken = gamestate.custom["laser_taken"]
        if laser_taken > 0:
            if gamestate.distance < 30:
                self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                if smashbro_state.action_frame == 1:
                    print('laser taken, ftilt attempted')
                return
            else:
                radius = 4
                self.pickchain(Chains.DashDance, [pivotpoint, radius])
                if smashbro_state.action_frame == 1:
                    print('laser taken, dashback attempted')
                return

        # ground options:
        # grab, 7/30 or 8/40,
        # tilt, 5/28, mid % and close
        # dsmash, 5/46, close and fastfaller
        # dash attack, 6/36, high % and far
        # usmash, 12/40, high % for floaty
        # nair, 6/?, high % and close

        # air options:
        # fair, 5/33, close-catchall
        # bair, 4/37, far and low % or at high %
        # nair, 3/48, falling or at high %
        # dair, 15/48, high %

        # TODO add dshffl to zone at edge
        if edgedistance < 15 and abs(smashbro_state.position.x) < 23:
            if not facingop and opoutside:
                self.pickchain(Chains.Dshffl, [DSHFFL_DIRECTION.BACK])
                if smashbro_state.action_frame == 1:
                    print('challenge edge dshffl bair')
                return

        # MOVEMENT BASED
        if approaching:
            if not opponent_state.on_ground and relative_y > 10:
                if not facingop:
                    self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.BACK])
                    if smashbro_state.action_frame == 1:
                        print('challenge intercept bair')
                    return
                if smashbro_state.action in [Action.STANDING] and 5 < diff_x < 17 and opponent_state.percent < 70:
                    self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                    if smashbro_state.action_frame == 1:
                        print('challenge intercept ftilt')
                    return
            if floaty and facingop:
                if smashbro_state.action in [Action.STANDING, Action.TURNING]:
                    if 5 < diff_x < 17 and 15 < opponent_state.percent < 60:
                        self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                        if smashbro_state.action_frame == 1:
                            print('challenge intercept ftilt')
                        return
                    if opponent_state.percent > 50 and diff_x < 13:
                        self.pickchain(Chains.Jab)
                        if smashbro_state.action_frame == 1:
                            print('challenge jab')
                        return

        # op above
        if smashbro_state.position.y < opponent_state.position.y:
            # op falling on smashbro
            if opponentyvelocity < 0:
                if smashbro_state.action in [Action.DASHING, Action.RUNNING] and facingop and 20 < diff_x < 25 \
                         and relative_y < 15 and opponent_state.percent > 40 and facingop:
                    self.pickchain(Chains.DashAttack)
                    if smashbro_state.action_frame == 1:
                        print('challenge dash attack')
                    return
                if smashbro_state.action in [Action.STANDING, Action.TURNING] and facingop and gamestate.distance < 14:
                    if floaty:
                        if opponent_state.percent > 100 or DI_up and relative_y > 10:
                            self.pickchain(Chains.Jab)
                            if smashbro_state.action_frame == 1:
                                print('challenge jab')
                            return
                        if opponent_state.percent < 80 and diff_x < 7 and 5 < relative_y < 10:
                            self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                            if smashbro_state.action_frame == 1:
                                print('challenge ftilt')
                            return
                        if opponent_state.percent > 20 or DI_up:
                            self.pickchain(Chains.Tilt, [TILT_DIRECTION.DOWN])
                            if smashbro_state.action_frame == 1:
                                print('challenge dtilt')
                            return
                    else:
                        self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                        if smashbro_state.action_frame == 1:
                            print('challenge ftilt')
                        return
                if smashbro_state.action in [Action.STANDING, Action.TURNING] and diff_x < 5:
                    self.pickchain(Chains.Tilt, [TILT_DIRECTION.UP])
                    if smashbro_state.action_frame == 1:
                        print('challenge utilt')
                    return
            # op above, but not falling (pretty much at the apex of their air time)
            if diff_x > 10 and opoutside:
                if facingop:
                    if opponent_state.position.y < -5:
                        self.pickchain(Chains.Dshffl, [DSHFFL_DIRECTION.FORWARD])
                        if smashbro_state.action_frame == 1:
                            print('challenge dshffl fair')
                        return
                    else:
                        self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.FORWARD])
                        if smashbro_state.action_frame == 1:
                            print('challenge shffl fair')
                        return
                else:
                    self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.BACK])
                    if smashbro_state.action_frame == 1:
                        print('challenge shffl bair')
                    return
            if diff_x < 10:
                if floaty and 9 < relative_y < 15 and smashbro_state.on_ground:
                    self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                    if smashbro_state.action_frame == 1:
                        print('challenge dthrow')
                    return
                if opoutside and not DI_out:
                    self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.NEUTRAL])
                    if smashbro_state.action_frame == 1:
                        print('challenge shffl nair')
                    return
                if diff_y > 25 and diff_x < 5:
                    self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.UP])
                    if smashbro_state.action_frame == 1:
                        print('challenge shffl uair')
                    return

        # falling
        if smashbro_state.speed_y_self < 0 and not smashbro_state.on_ground:
            if facingop:
                if opponent_state.percent > 25 or opponent_state.on_ground:
                    self.pickchain(Chains.FallingAerial, [FALLING_AERIAL_DIRECTION.FORWARD])
                    if smashbro_state.action_frame == 1:
                        print('challenge falling fair')
                    return
            elif not facingop and diff_x > 10:
                self.pickchain(Chains.FallingAerial, [FALLING_AERIAL_DIRECTION.BACK])
                if smashbro_state.action_frame == 1:
                    print('challenge falling bair')
                return
            else:
                self.pickchain(Chains.FallingAerial, [FALLING_AERIAL_DIRECTION.NEUTRAL])
                if smashbro_state.action_frame == 1:
                    print('challenge falling nair')
                return

        # challenge landing, essentially a punish
        if opponent_state.action in landing and diff_y < 3 and smashbro_state.on_ground:
            if floaty and facingop and diff_x < 17 and opponent_state.percent > 100 or DI_up:
                if smashbro_state.action in [Action.STANDING, Action.TURNING]:
                    self.pickchain(Chains.Jab)
                    if smashbro_state.action_frame == 1:
                        print('challenge landing jab')
                    return
            if facingop and 15 < opponent_state.percent < 60:
                if smashbro_state.action in [Action.STANDING] and 5 < diff_x < 17:
                    self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                    if smashbro_state.action_frame == 1:
                        print('challenge landing ftilt')
                    return
                if smashbro_state.action in [Action.STANDING, Action.TURNING] and diff_x < 5 \
                        and opponent_state.action not in crouching:
                    self.pickchain(Chains.Tilt, [TILT_DIRECTION.UP])
                    if smashbro_state.action_frame == 1:
                        print('challenge landing utilt')
                    return
            if facingop and smashbro_state.action not in actionexclude:
                self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                if smashbro_state.action_frame == 1:
                    print('challenge landing dthrow')
                return

        # POSITION BASED
        # side platform stuff
        lowest_plat = 22  # current lowest platform position

        if smashbro_state.position.y > lowest_plat and gamestate.stage != melee.enums.Stage.FINAL_DESTINATION:
            # drop cancel nair, requires a platform that can be fallen through
            if grounded_actionable or smashbro_state.action in [Action.PLATFORM_DROP, Action.FALLING, Action.NAIR] \
                    and gamestate.distance < 8:
                self.pickchain(Chains.DropCancelNair)
                if smashbro_state.action_frame == 1:
                    print('challenge drop cancel nair')
                return
            # platform drop fair
            if grounded_actionable or smashbro_state.action in [Action.PLATFORM_DROP, Action.FALLING] \
                    and 5 < gamestate.distance < 15 and facingop:
                self.pickchain(Chains.DropFair)
                if smashbro_state.action_frame == 1:
                    print('challenge drop fair')
                return

        on_main_platform = smashbro_state.position.y < 1 and smashbro_state.on_ground
        if opponent_state.position.y > 1 and opponent_state.on_ground and on_main_platform and gamestate.stage != melee.enums.Stage.FOUNTAIN_OF_DREAMS:
            self.pickchain(Chains.BoardSidePlatform, [opponent_state.position.x > 0])
            # print('board side platform')
            return

        # close range
        if diff_x < 10 and diff_y < 10 and (smashbro_state.on_ground or not opponent_state.on_ground):
            if heavy and smashbro_state.action in [Action.STANDING, Action.DASHING, Action.RUNNING]:
                if DI_down or opponent_state.action in crouching:
                    if smashbro_state.on_ground and (diff_x < 3 or (diff_x < 10 and opponent_state.percent > 70)):
                        self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                        if smashbro_state.action_frame == 1:
                            print('challenge dsmash')
                        return
                    if facingop and smashbro_state.on_ground:
                        self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                        if smashbro_state.action_frame == 1:
                            print('challenge dthrow')
                        return
            if smashbro_state.action in [Action.STANDING]:
                if facingop and opponent_state.action not in crouching and 15 < opponent_state.percent < 70:
                    self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                    if smashbro_state.action_frame == 1:
                        print('challenge ftilt')
                    return
            if smashbro_state.on_ground and (opponent_state.percent > 70 or not DI_down):
                if facingop:
                    if floaty:
                        if 20 < opponent_state.percent < 60 or not DI_down and DI_out:
                            self.pickchain(Chains.Tilt, [TILT_DIRECTION.DOWN])
                            if smashbro_state.action_frame == 1:
                                print('challenge dtilt')
                            return
                        if smashbro_state.action in [Action.STANDING, Action.TURNING]:
                            if opponent_state.percent > 100 or DI_up:
                                self.pickchain(Chains.Jab)
                                if smashbro_state.action_frame == 1:
                                    print('challenge jab')
                                return
                            if opponent_state.percent < 60 or DI_in:
                                self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                                if smashbro_state.action_frame == 1:
                                    print('challenge ftilt')
                                return
                if diff_x < 3 or (diff_x < 10 and opponent_state.percent > 70):
                    self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                    if smashbro_state.action_frame == 1:
                        print('challenge dsmash')
                    return
            if floaty and not facingop and opponentonright != opponent_state.facing:  # opponent facing bro
                if gamestate.custom["grab_fraction"] < 25:
                    if smashbro_state.percent < 50:
                        self.pickchain(Chains.Crouchcancel)
                        if smashbro_state.action_frame == 1:
                            print('challenge crouch cancel called')
                        return

        # midrange
        if 20 < diff_x < 25 and relative_y < 12:
            if smashbro_state.on_ground:
                if smashbro_state.action in [Action.RUNNING, Action.DASHING]:
                    if facingop and opponent_state.percent > 25:
                        self.pickchain(Chains.DashAttack)
                        if smashbro_state.action_frame == 1:
                            print('challenge dash attack')
                        return

        # TODO wavedash in
        # Shield actions
        if smashbro_state.action in [Action.SHIELD, Action.SHIELD_REFLECT]:
            # wavedash back
            self.pickchain(Chains.Wavedash, [1.0, False])
            if smashbro_state.action_frame == 1:
                print('wavedash oos')
            return

        if smashbro_state.position.y > lowest_plat and smashbro_state.on_ground is True:
            print('CHALLENGE: on platform')

        # Otherwise dash dance to the pivot point
        self.pickchain(Chains.DashDance, [pivotpoint, dashdanceradius, False])
