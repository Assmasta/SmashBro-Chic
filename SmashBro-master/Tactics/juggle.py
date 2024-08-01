import melee
import Chains
import random
from melee.enums import Action, Character, Stage
from Tactics.tactic import Tactic
from Chains.tilt import TILT_DIRECTION
from Chains.grabandthrow import THROW_DIRECTION
from Chains.airattack import AirAttack, AIR_ATTACK_DIRECTION
from Tactics.punish import Punish
from Chains.shffl import SHFFL_DIRECTION
from Chains.smashattack import SMASH_DIRECTION
from Chains.dshffl import DSHFFL_DIRECTION

# TODO getting under helpless airborne opponents

class Juggle(Tactic):
    def __init__(self, logger, controller, framedata, difficulty):
        Tactic.__init__(self, logger, controller, framedata, difficulty)

    def canjuggle(smashbro_state, opponent_state, gamestate, framedata, difficulty):
        if opponent_state.invulnerability_left > 0:
            return False

        if smashbro_state.off_stage:
            return False

        # If the opponent is in hitstun, in the air
        if (not opponent_state.on_ground) and (opponent_state.hitstun_frames_left > 0):
            if not framedata.is_attack(opponent_state.character, opponent_state.action):
                return True

        # If opponent is airborne and has no jumps
        if (not opponent_state.on_ground) and opponent_state.jumps_left == 0:
            if not framedata.is_attack(opponent_state.character, opponent_state.action):
                return True

        # If opponent is falling helplessly
        if opponent_state.action == Action.DEAD_FALL:
            return True

        return False

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        # If we can't interrupt the chain, just continue it
        if self.chain != None and not self.chain.interruptible:
            self.chain.step(gamestate, smashbro_state, opponent_state)
            return

        # Get over to where they will end up at the end of hitstun
        end_x, end_y, frames_left = self.framedata.project_hit_location(opponent_state, gamestate.stage)

        if self.framedata.is_roll(opponent_state.character, opponent_state.action):
            end_x = self.framedata.roll_end_position(opponent_state, gamestate.stage) + self.framedata.slide_distance(opponent_state, opponent_state.speed_x_attack, frames_left)
            frames_left = self.framedata.last_roll_frame(opponent_state.character, opponent_state.action) - opponent_state.action_frame

        facing_away = (smashbro_state.position.x < end_x) != smashbro_state.facing
        if smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
            facing_away = not facing_away

        on_ground = opponent_state.on_ground or opponent_state.position.y < 1 or opponent_state.action in [Action.TECH_MISS_UP, Action.TECH_MISS_DOWN]

        # Make sure we don't dashdance off the platform during a juggle
        side_platform_height, side_platform_left, side_platform_right = melee.side_platform_position(opponent_state.position.x > 0, gamestate.stage)
        top_platform_height, top_platform_left, top_platform_right = melee.top_platform_position(gamestate.stage)
        if opponent_state.position.y < 5:
            end_x = min(end_x, melee.EDGE_GROUND_POSITION[gamestate.stage]-5)
            end_x = max(end_x, -melee.EDGE_GROUND_POSITION[gamestate.stage]+5)
        elif (side_platform_height is not None) and abs(opponent_state.position.y - side_platform_height) < 5:
            end_x = min(end_x, side_platform_right-5)
            end_x = max(end_x, side_platform_left+5)
        elif (top_platform_height is not None) and abs(opponent_state.position.y - top_platform_height) < 5:
            end_x = min(end_x, top_platform_right-5)
            end_x = max(end_x, top_platform_left+5)

        if self.logger:
            self.logger.log("Notes", " Predicted End Position: " + str(end_x) + " " + str(end_y) + " ", concat=True)
            self.logger.log("Notes", " on_ground: " + str(on_ground), concat=True)
            self.logger.log("Notes", " frames left: " + str(frames_left) + " ", concat=True)

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

        teching = opponent_state.action in [Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN, Action.BACKWARD_TECH,
                                            Action.TECH_MISS_DOWN,
                                            Action.TECH_MISS_UP, Action.NEUTRAL_TECH, Action.GROUND_ROLL_BACKWARD_UP,
                                            Action.GROUND_ROLL_BACKWARD_DOWN]

        diff_y = round(abs(smashbro_state.position.y - opponent_state.position.y), 2)
        diff_x = round(abs(opponent_state.position.x - smashbro_state.position.x), 2)
        relative_y = round(opponent_state.position.y - smashbro_state.position.y, 2)

        DI_up = "up" in gamestate.custom["predominant_SDI_direction"]
        DI_down = "down" in gamestate.custom["predominant_SDI_direction"]
        DI_in = "in" in gamestate.custom["predominant_SDI_direction"]
        DI_out = "out" in gamestate.custom["predominant_SDI_direction"]

        opoutside = abs(smashbro_state.position.x) < abs(opponent_state.position.x)
        edgedistance = melee.stages.EDGE_GROUND_POSITION[gamestate.stage] - abs(smashbro_state.position.x)

        # op falling on smashbro and regrab
        regrabbable_position_close = 0 < diff_x < 23 and 9 < relative_y < 15
        regrabbable_position_far = 23 < diff_x < 30 and 12 < relative_y < 18
        regrabbable = opponent_state.action in [Action.DAMAGE_FLY_TOP, Action.FALLING] \
                      and not facing_away and smashbro_state.on_ground \
                      and (regrabbable_position_close or regrabbable_position_far)
        if regrabbable:
            # dthrow for midair regrab
            if floaty:
                self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                if smashbro_state.action_frame == 1:
                    print('juggle catching dthrow')
                return

        # TODO add dshffl to zone at edge
        if edgedistance < 15 and abs(smashbro_state.position.x) < 23:
            if facing_away and opoutside:
                self.pickchain(Chains.Dshffl, [DSHFFL_DIRECTION.BACK])
                if smashbro_state.action_frame == 1:
                    print('juggle edge dshffl bair')
                return

        if not on_ground:
            # 7 frames later
            end_early_x, end_early_y, _ = self.framedata.project_hit_location(opponent_state, gamestate.stage, 7)
            if self.logger:
                self.logger.log("Notes", " uptilt early End Position: " + str(end_early_x) + " " + str(end_early_y) + " ", concat=True)
            x_target_range = abs(end_early_x - smashbro_state.position.x)
            y_target_range = abs(end_early_y - smashbro_state.position.y)
            in_range = (x_target_range < 15) and (y_target_range < 30)
            if smashbro_state.action in [Action.TURNING, Action.STANDING, Action.DASHING]:
                if in_range:
                    # add (x, y, facing), action, percent, fall-speed and weight class and other conditions
                    self.chain = None  # jabs, tilts, aerials, usmash, dair if hitstun > 12
                    if opponent_state.hitstun_frames_left > 12 and opponent_state.percent < 90 and floaty:
                        if side_platform_left < opponent_state.position.x < side_platform_right:
                            self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.FORWARD])
                            if smashbro_state.action_frame == 1:
                                print('juggle shffl fair')
                            return
                        else:
                            self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.DOWN])
                            if smashbro_state.action_frame == 1:
                                print('juggle shffl dair')
                            return
                    if floaty:
                        if opponent_state.percent < 50:
                            if 12 < y_target_range and x_target_range < 10:
                                self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.UP])
                                if smashbro_state.action_frame == 1:
                                    print('juggle shffl uair')
                                return
                        if smashbro_state.action in [Action.STANDING] and not facing_away and not DI_out:
                            if DI_up and y_target_range < 8:
                                self.pickchain(Chains.Tilt, [TILT_DIRECTION.DOWN])
                                if smashbro_state.action_frame == 1:
                                    print('juggle dtilt')
                                return
                            if not DI_up and y_target_range < 10:
                                self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                                if smashbro_state.action_frame == 1:
                                    print('juggle ftilt')
                                return
                        if opponent_state.percent > 70:
                            if x_target_range < 15 and not facing_away:
                                self.pickchain(Chains.Shffl, [SHFFL_DIRECTION.FORWARD])
                                if smashbro_state.action_frame == 1:
                                    print('juggle shffl fair')
                                return

                    # generic fall-speed branch
                    if opponent_state.percent < 50:
                        if x_target_range < 5 and 2 < y_target_range < 15:
                            self.pickchain(Chains.Tilt, [TILT_DIRECTION.UP])
                            if smashbro_state.action_frame == 1:
                                print('juggle utilt')
                            return

            # Check each height level, can we do an aerial right now?
            for height_level in AirAttack.height_levels():
                height = AirAttack.attack_height(height_level)
                commitment = AirAttack.frame_commitment(height_level)
                end_early_x, end_early_y, _ = self.framedata.project_hit_location(opponent_state, gamestate.stage, commitment)
                # commitment and x-axis size
                if commitment < frames_left and x_target_range < 25:
                    # height
                    if 5 < ((height+smashbro_state.position.y) - end_early_y) < 20:
                        self.chain = None
                        if not facing_away and opponent_state.percent > 40 and x_target_range < 15 and \
                                5 < ((height+smashbro_state.position.y) - end_early_y):
                            self.pickchain(Chains.AirAttack,
                                           [end_early_x, end_early_y, height_level, AIR_ATTACK_DIRECTION.FORWARD])
                            if smashbro_state.action_frame == 1:
                                print('juggle fair', round(diff_y, 0))
                            return
                        elif x_target_range < 5 and 15 < ((height+smashbro_state.position.y) - end_early_y) < 20:
                            self.pickchain(Chains.AirAttack,
                                           [end_early_x, end_early_y, height_level, AIR_ATTACK_DIRECTION.UP])
                            if smashbro_state.action_frame == 1:
                                print('juggle uair', round(diff_y, 0))
                            return
                        elif facing_away and 10 < x_target_range < 20:
                            self.pickchain(Chains.AirAttack,
                                           [end_early_x, end_early_y, height_level, AIR_ATTACK_DIRECTION.BACK])
                            if smashbro_state.action_frame == 1:
                                print('juggle bair', round(diff_y, 0))
                            return

            # TODO: platform chase
            # They are going to land on a platform before hitstun ends
            if frames_left < opponent_state.hitstun_frames_left and end_y > 0:
                # Board the platform they're going to
                if end_y > 40:
                    self.chain = None
                    self.pickchain(Chains.BoardTopPlatform)
                    return
                else:
                    self.chain = None
                    self.pickchain(Chains.BoardSidePlatform, [end_x > 0, False])
                    return

            # Just dash dance to where they will end up
            if frames_left > 9:
                self.chain = None
                self.pickchain(Chains.DashDance, [end_x])
                return
        else:
            # We're further than 5 units away, so DD into their end position
            self.chain = None
            self.pickchain(Chains.DashDance, [end_x])
            return

        self.chain = None
        self.pickchain(Chains.Nothing)
