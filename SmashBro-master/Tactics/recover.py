import melee
import Chains
import random
import math
from melee.enums import Action, Button
from enum import Enum
from Tactics.punish import Punish
from Tactics.tactic import Tactic
from Chains.aerial import Aerial, AERIAL_DIRECTION
from Chains.vanish import DIRECTION
from Chains.edgeaerial import EdgeAerial, EDGE_AERIAL_DIRECTION

# TODO edgeguard flanking

class Recover(Tactic):
    # Do we need to recover?
    def needsrecovery(smashbro_state, opponent_state, gamestate):
        onedge = smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]
        opponentonedge = opponent_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING, Action.EDGE_GETUP_SLOW, \
        Action.EDGE_GETUP_QUICK, Action.EDGE_ATTACK_SLOW, Action.EDGE_ATTACK_QUICK, Action.EDGE_ROLL_SLOW, Action.EDGE_ROLL_QUICK]

        # If the opponent is on-stage, and Smashbro is on-edge, Smashbro needs to ledgedash
        if not opponent_state.off_stage and onedge:
            return True

        # If we're on stage, then we don't need to recover
        if not smashbro_state.off_stage:
            return False

        if smashbro_state.on_ground:
            return False

        # We can now assume that we're off the stage...

        # If opponent is dead
        if opponent_state.action in [Action.DEAD_DOWN, Action.DEAD_RIGHT, Action.DEAD_LEFT, \
                Action.DEAD_FLY, Action.DEAD_FLY_STAR, Action.DEAD_FLY_SPLATTER]:
            return True

        # If opponent is on stage
        if not opponent_state.off_stage:
            return True

        # If opponent is in hitstun, then recover, unless we're on the edge.
        if opponent_state.off_stage and opponent_state.hitstun_frames_left > 0 and not onedge:
            return True

        if opponent_state.action == Action.DEAD_FALL and opponent_state.position.y < -30:
            return True

        # If opponent is closer to the edge, recover
        diff_x_opponent = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(opponent_state.position.x))
        diff_x = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(smashbro_state.position.x))

        # Using (opponent_state.position.y + 15)**2 was causing a keepdistance/dashdance bug.
        opponent_dist = math.sqrt( (opponent_state.position.y)**2 + (diff_x_opponent)**2 )
        smashbro_dist = math.sqrt( (smashbro_state.position.y)**2 + (diff_x)**2 )

        if opponent_dist < smashbro_dist and not onedge:
            return True

        if smashbro_dist >= 20:
            return True

        # If we're both fully off stage, recover
        if opponent_state.off_stage and smashbro_state.off_stage and not onedge and not opponentonedge:
            return True

        # If opponent is ON the edge, recover
        if opponentonedge and not onedge:
            return True

        if -100 < smashbro_state.position.y < -50:
            return True

        return False

    def __init__(self, logger, controller, framedata, difficulty):
        Tactic.__init__(self, logger, controller, framedata, difficulty)
        # We need to decide how we want to recover
        self.logger = logger

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        opponentonedge = opponent_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING, Action.EDGE_GETUP_SLOW, \
        Action.EDGE_GETUP_QUICK, Action.EDGE_ATTACK_SLOW, Action.EDGE_ATTACK_QUICK, Action.EDGE_ROLL_SLOW, Action.EDGE_ROLL_QUICK]

        # If we can't interrupt the chain, just continue it
        if self.chain != None and not self.chain.interruptible:
            self.chain.step(gamestate, smashbro_state, opponent_state)
            return

        if gamestate.stage == melee.enums.Stage.YOSHIS_STORY:
            lower_corner = (melee.stages.EDGE_POSITION[gamestate.stage], -1000)
        if gamestate.stage == melee.enums.Stage.BATTLEFIELD:
            lower_corner = (melee.stages.EDGE_POSITION[gamestate.stage], -10)
        if gamestate.stage == melee.enums.Stage.FINAL_DESTINATION:
            lower_corner = (45, -66.21936)
        if gamestate.stage == melee.enums.Stage.DREAMLAND:
            lower_corner = (63, -47.480972)
        if gamestate.stage == melee.enums.Stage.POKEMON_STADIUM:
            lower_corner = (70, -29.224771)

        # for the purposes of recovery, diff_x will denote distance from the edge, instead of opponent
        diff_x = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(smashbro_state.position.x))
        diff_x_opponent = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(opponent_state.position.x))

        # If we can just grab the edge with a vanish, do that
        facinginwards = smashbro_state.facing == (smashbro_state.position.x < 0)
        if not facinginwards and smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
            facinginwards = True

        # under stage
        understage = False
        if abs(smashbro_state.position.x) + 4 < melee.stages.EDGE_POSITION[gamestate.stage] and smashbro_state.position.y < 0:
            understage = True

        # vanish check
        midvanish = False
        if smashbro_state.action in [Action.SWORD_DANCE_1_AIR, Action.SWORD_DANCE_2_HIGH_AIR]:
            midvanish = True

        landing = [Action.LANDING, Action.LANDING_SPECIAL, Action.NAIR_LANDING, Action.FAIR_LANDING,
                                     Action.BAIR_LANDING, Action. UAIR_LANDING, Action.DAIR_LANDING]

        ys_true = gamestate.stage == melee.enums.Stage.YOSHIS_STORY

        # TODO ledgehop reverse fair, bair and dair
        if smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]:
            if 5 < abs(smashbro_state.position.x) - abs(opponent_state.position.x) < 10 and -2 < opponent_state.position.y < 10:
                if opponent_state.action in landing or not opponent_state.on_ground:  # 7 frames
                    self.chain = None
                    self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.FORWARD])
                    return
            else:  # It takes 22 frames to go from frame 1 of hanging to standing.
                frames_left = Punish.framesleft(opponent_state, self.framedata, smashbro_state)
                refresh = frames_left < 22 and smashbro_state.invulnerability_left <= 1
                self.pickchain(Chains.Edgedash, [refresh])
                return

        if not midvanish:
            if smashbro_state.action == Action.DEAD_FALL:
                self.chain = None
                self.pickchain(Chains.DI, [int(smashbro_state.position.x < 0), 0.5])
                return
        # edgeguard continuation
            if abs(smashbro_state.position.x) < abs(opponent_state.position.x) and smashbro_state.position.y > -30: \
                    #and gamestate.stage != melee.enums.Stage.YOSHIS_STORY:
                if -20 < opponent_state.position.y < 25 and not opponent_state.on_ground \
                        and 10 < gamestate.distance < 20 and opponent_state.percent > 45 \
                        and not facinginwards and not (diff_x_opponent < 15 and opponent_state.position.y < 0):
                    self.chain = None
                    self.pickchain(Chains.Runofffair)
                    diff_x_opponent = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(opponent_state.position.x))
                    print('Recovery: opponent position', round(diff_x_opponent, 0), round(opponent_state.position.y, 0))
                    if smashbro_state.action_frame == 1:
                        print('recover runoff fair')
                    return
            if (not facinginwards or smashbro_state.action in [Action.NEUTRAL_B_CHARGING_AIR, Action.WAIT_ITEM]) \
                    and ((smashbro_state.position.y > -70 and not ys_true) or smashbro_state.position.y > -30) \
                    and not understage:
                self.chain = None
                self.pickchain(Chains.NeedleReverse)
                return

            # If we can just do nothing and grab the edge, do that
            # _____ can ledgegrab from behind in this animation, but he oftentimes needs to fastfall to hit the window.
            if -12 < smashbro_state.position.y and (diff_x < 10) and (facinginwards or smashbro_state.action == Action.SWORD_DANCE_1_AIR) and smashbro_state.speed_y_self <= 0:
                # Do a Fastfall if we're not already
                if smashbro_state.action == Action.FALLING and smashbro_state.speed_y_self > -3 and smashbro_state.position.y >= 0:
                    self.chain = None
                    self.pickchain(Chains.DI, [0.5, 0])
                    return

                # If we are currently moving away from the stage, DI in
                if (smashbro_state.speed_air_x_self > 0) == (smashbro_state.position.x > 0):
                    x = 0
                    if smashbro_state.position.x < 0:
                        x = 1
                    self.chain = None
                    self.pickchain(Chains.DI, [x, 0.5])
                    return
                else:
                    self.pickchain(Chains.Nothing)
                    return


        # look out for edgehogs
        opponent_edgedistance = abs(opponent_state.position.x) - abs(melee.stages.EDGE_GROUND_POSITION[gamestate.stage])
        opponentfacinginwards = opponent_state.facing == (opponent_state.position.x < 0)
        if not opponentfacinginwards and opponent_state.action == Action.TURNING and opponent_state.action_frame == 1:
            opponentfacinginwards = True
        opponentpotentialedgehog = False
        if opponentfacinginwards and opponent_edgedistance < 15 and -30 < opponent_state.position.y < 5:
            opponentpotentialedgehog = True

        # Is the opponent going offstage to edgeguard us?
        opponent_edgedistance = abs(opponent_state.position.x) - abs(melee.stages.EDGE_GROUND_POSITION[gamestate.stage])
        opponent_verticaldistance = abs(smashbro_state.position.y - opponent_state.position.y)
        opponentxvelocity = opponent_state.speed_air_x_self + opponent_state.speed_ground_x_self
        opponentmovingtoedge = not opponent_state.off_stage and (opponent_edgedistance < 20) and (
                    opponentxvelocity > 0 == opponent_state.position.x > 0)
        opponentgoingoffstage = opponent_state.action in [Action.FALLING, Action.JUMPING_FORWARD, Action.JUMPING_BACKWARD,
                                                          Action.LANDING_SPECIAL, Action.DASHING, Action.WALK_MIDDLE,
                                                          Action.WALK_FAST, Action.NAIR, Action.FAIR, Action.UAIR,
                                                          Action.BAIR, Action.DAIR]
        # recovery options
        # 1 high vanish
        # 2 sweet-spot vanish
        # 3 double jump to ledge
        # 4 double jump fair to ledge
        # 5 air dodge to ledge

        # proximity aerial
        if (smashbro_state.position.y > 10 or (smashbro_state.position.y > -20 and smashbro_state.speed_y_self > 0 and not ys_true)) \
                and opponent_state.off_stage and facinginwards:
            if 15 < abs(smashbro_state.position.x) - abs(opponent_state.position.x) < 25 \
                    and opponent_verticaldistance < 10:
                self.pickchain(Chains.Aerial, [AERIAL_DIRECTION.FORWARD])
                return
            if 15 < abs(opponent_state.position.x) - abs(smashbro_state.position.x) < 25 \
                    and opponent_verticaldistance < 10 and diff_x < 20:  # op outside
                self.pickchain(Chains.Aerial, [AERIAL_DIRECTION.BACK])
                return

        # vanish: 66.42 vertical, ledgegrab 23 above
        # If we're lined up, do the vanish
        # diagonal 47.5 height, 51.61 horizontal
        # forward 67 horizontal
        # recovery part 1 moves us up 27 units everytime, with a possible horizontal drift of 25 units
        min_height_horizontal = -45
        if gamestate.stage in [melee.enums.Stage.BATTLEFIELD, melee.enums.Stage.POKEMON_STADIUM]:
            min_height_horizontal = -38
        min_height_diagonal = -73
        if gamestate.stage in [melee.enums.Stage.BATTLEFIELD, melee.enums.Stage.POKEMON_STADIUM]:
            min_height_diagonal = -66
        min_height_vertical = -90
        if gamestate.stage in [melee.enums.Stage.BATTLEFIELD, melee.enums.Stage.POKEMON_STADIUM]:
            min_height_vertical = -83

        # 1 HIGH RECOVERY
        # used if opponent on the edge, or below the stage and closer to the edge
        # if far from edge, use jump to get closer
        if smashbro_state.jumps_left > 0 and diff_x > 100:
            self.pickchain(Chains.Jump)
            if smashbro_state.action_frame == 1:
                print('jump: far double jump', round(diff_x, 0), round(smashbro_state.position.y, 0))
            return
        # recover as high as possible
        if opponentpotentialedgehog:
            # print('opponent potential edgehog')
            # avoid potentially jumping into horizontal projectiles
            if smashbro_state.jumps_left > 0:
                if abs(smashbro_state.position.y) > 20 and not understage:
                    self.pickchain(Chains.Jump)
                    if smashbro_state.action_frame == 1:
                        print('jump: avoid edgehog double jump', round(diff_x, 0), round(smashbro_state.position.y, 0))
                    return
                if smashbro_state.position.y < -40 and understage:
                    self.pickchain(Chains.Jump)
                    return
        # 2 AMBIGUOUS RECOVERY
        # near the edge, will need mix up, either go up, diagonal up or forward
            if (0 < abs(smashbro_state.position.y) < diff_x < 30) or midvanish:
                vanish_rng = random.randint(0, 4)
                if vanish_rng == 0 and smashbro_state.position.y > 0:
                    self.pickchain(Chains.Vanish, [DIRECTION.FORWARD])
                    if smashbro_state.action_frame == 1:
                        print('horizontal vanish high', round(smashbro_state.position.y, 0))
                    return
                if vanish_rng == 1 and diff_x < 6:
                    self.pickchain(Chains.Vanish, [DIRECTION.UP])
                    if smashbro_state.action_frame == 1:
                        print('vertical vanish high', round(smashbro_state.position.y, 0))
                    return
                else:
                    self.pickchain(Chains.Vanish, [DIRECTION.DIAGONALUP])
                    if smashbro_state.action_frame == 1:
                        print('diagonal vanish high', round(smashbro_state.position.y, 0))
                    return

        # 3 SWEET-SPOT
        # horizontal vanish, no minimum distance
        if (min_height_horizontal < smashbro_state.position.y < min_height_horizontal + 2) or midvanish:
            self.pickchain(Chains.Vanish, [DIRECTION.FORWARD])
            if smashbro_state.action_frame == 1:
                print('horizontal vanish to ledge sweetspot')
            return
        # diagonal vanish up
        if diff_x > 26:  # for the purposes of recovery, diff_x will denote distance from the edge, instead of opponent
            if (min_height_diagonal < smashbro_state.position.y < min_height_diagonal + 2) or midvanish:
                self.pickchain(Chains.Vanish, [DIRECTION.DIAGONALUP])
                if smashbro_state.action_frame == 1:
                    print('diagonal vanish to ledge sweetspot')
                return
        # vertical vanish
        if diff_x < 13 and (not understage or diff_x < 5):
            if (min_height_vertical < smashbro_state.position.y < min_height_vertical + 2) or midvanish:
                self.pickchain(Chains.Vanish, [DIRECTION.UP])
                if smashbro_state.action_frame == 1:
                    print('vertical vanish to ledge sweetspot')
                return

        # low double jump, probably only good for stalling
        if smashbro_state.jumps_left > 0 and (-110 < smashbro_state.position.y < -70 or
                 (gamestate.stage == melee.enums.Stage.YOSHIS_STORY and smashbro_state.position.y < -50)):
            self.pickchain(Chains.Jump)
            if smashbro_state.action_frame == 1:
                print('jump: low double jump', round(diff_x, 0), round(smashbro_state.position.y, 0))
            return

        # If we're high, just let ourselves fall into place
        if smashbro_state.position.y > -5 and not diff_x < 5:
            # DI into the stage
            x = 0
            if smashbro_state.position.x < 0:
                x = 1
            self.chain = None
            self.pickchain(Chains.DI, [x, 0.5])
            return

        # end needle reverse
        if smashbro_state.action in [Action.NEUTRAL_B_CHARGING_AIR, Action.WAIT_ITEM]:
            # cancel needles on frame 8
            if smashbro_state.action == Action.WAIT_ITEM:
                if smashbro_state.action_frame >= 8:
                    self.interruptible = False
                    self.controller.press_button(Button.BUTTON_L)
                    self.controller.release_button(Button.BUTTON_B)
                    return
                else:
                    self.interruptible = False
                    self.controller.press_button(Button.BUTTON_B)
                    self.controller.tilt_analog(Button.BUTTON_MAIN, .5, .5)
                    return
            else:
                self.interruptible = False
                self.controller.press_button(Button.BUTTON_L)
                return

        # vanish catch-all
        if smashbro_state.action == Action.SWORD_DANCE_1_AIR and 34 <= smashbro_state.action_frame <= 35 \
                and not facinginwards:
            # point inwards just in case facing wrong way
            self.pickchain(Chains.Vanish, [DIRECTION.UP])
            return

        # for vanish purposes
        y = 0.5
        if smashbro_state.jumps_left == 0:
            y = 1

        # DI inward
        if not understage and not diff_x < 5:
            x = 0
            if smashbro_state.position.x < 0:
                x = 1
            self.chain = None
            self.pickchain(Chains.DI, [x, y])

