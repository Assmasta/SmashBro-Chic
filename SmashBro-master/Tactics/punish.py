import melee
import Chains
import random
import math
from melee.enums import Action, Button, Character
from Tactics.tactic import Tactic
from Chains.smashattack import SMASH_DIRECTION
from Chains.shffl import SHFFL_DIRECTION
from Chains.shieldaction import SHIELD_ACTION
from Chains.airattack import AirAttack, AIR_ATTACK_DIRECTION
from Chains.grabandthrow import THROW_DIRECTION
from Chains.tilt import TILT_DIRECTION
from Chains.dshffl import DSHFFL_DIRECTION

# TODO punish grounded attacks
#   approach with shield
#   increase bubble range for dd
#   treat recoil as opening

class Punish(Tactic):
    # How many frames do we have to work with for the punish
    def framesleft(opponent_state, framedata, smashbro_state):
        # For some dumb reason, the game shows the standing animation as having a large hitstun
        #   manually account for this
        if opponent_state.action == Action.STANDING:
            return 1

        # Opponent's shield is broken, opponent is resting Puff.
        restingpuff = opponent_state.character == Character.JIGGLYPUFF and opponent_state.action == Action.MARTH_COUNTER
        if restingpuff or opponent_state.action in [Action.SHIELD_BREAK_STAND_U, Action.SHIELD_BREAK_TEETER]:
            return 249 - opponent_state.action_frame

        # Don't try to punish Samus knee_bend, because they will go into UP_B and it has invulnerability
        if opponent_state.action == Action.KNEE_BEND and opponent_state.character == Character.SAMUS:
            return 0

        # used to stop shining
        if opponent_state.position.y > 5 and opponent_state.action in [Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN]:
            return 0

        # Samus UP_B invulnerability
        if opponent_state.action in [Action.SWORD_DANCE_3_MID, Action.SWORD_DANCE_3_LOW] and \
                opponent_state.character == Character.SAMUS and opponent_state.action_frame <= 5:
            return 0

        # Samus morph ball
        if opponent_state.character == Character.SAMUS and opponent_state.action in [Action.SWORD_DANCE_4_MID, Action.SWORD_DANCE_4_HIGH, Action.NEUTRAL_B_CHARGING]:
            return 1

        # Pikachu skull bash, thunder
        if opponent_state.action in [Action.NEUTRAL_B_FULL_CHARGE, Action.NEUTRAL_B_ATTACKING, Action.SWORD_DANCE_2_MID_AIR, Action.SWORD_DANCE_2_HIGH_AIR] and \
                opponent_state.character == Character.PIKACHU:
            return 1

        # Jigglypuff jumps
        if opponent_state.character == Character.JIGGLYPUFF and opponent_state.action in \
                [Action.LASER_GUN_PULL, Action.NEUTRAL_B_CHARGING, Action.NEUTRAL_B_ATTACKING, Action.NEUTRAL_B_FULL_CHARGE, Action.WAIT_ITEM]:
            return 1

        if opponent_state.character == Character.SHEIK:
            if opponent_state.action in [Action.SWORD_DANCE_4_HIGH, Action.SWORD_DANCE_1_AIR]:
                return 17 - opponent_state.action_frame
            if opponent_state.action in [Action.SWORD_DANCE_4_LOW, Action.SWORD_DANCE_2_HIGH_AIR] and opponent_state.action_frame <= 21:
                return 0

        # Shine wait
        if opponent_state.character in [Character.FOX, Character.FALCO]:
            if opponent_state.action in [Action.SWORD_DANCE_2_MID_AIR, Action.SWORD_DANCE_3_HIGH_AIR, Action.SWORD_DANCE_3_LOW_AIR]:
                return 3

        if opponent_state.action == Action.LOOPING_ATTACK_MIDDLE:
            return 1

        if opponent_state.character == Character.SHEIK and opponent_state.action == Action.SWORD_DANCE_2_HIGH:
            return 1

        # Is opponent attacking?
        if framedata.is_attack(opponent_state.character, opponent_state.action):
            # What state of the attack is the opponent in?
            # Windup / Attacking / Cooldown
            attackstate = framedata.attack_state(opponent_state.character, opponent_state.action, opponent_state.action_frame)
            if attackstate == melee.enums.AttackState.WINDUP:
                # Don't try to punish opponent in windup when they're invulnerable
                if opponent_state.invulnerability_left > 0:
                    return 0
                # Don't try to punish standup attack windup
                if opponent_state.action in [Action.GROUND_ATTACK_UP, Action.GETUP_ATTACK]:
                    return 0
                frame = framedata.first_hitbox_frame(opponent_state.character, opponent_state.action)
                # Account for boost grab. Dash attack can cancel into a grab
                if opponent_state.action == Action.DASH_ATTACK:
                    return min(6, frame - opponent_state.action_frame - 1)
                return max(0, frame - opponent_state.action_frame - 1)
            if attackstate == melee.enums.AttackState.ATTACKING and smashbro_state.action == Action.SHIELD_RELEASE:
                if opponent_state.action in [Action.NAIR, Action.FAIR, Action.UAIR, Action.BAIR, Action.DAIR]:
                    return 7
                elif opponent_state.character == Character.PEACH and opponent_state.action in [Action.NEUTRAL_B_FULL_CHARGE, Action.WAIT_ITEM, Action.NEUTRAL_B_ATTACKING, Action.NEUTRAL_B_CHARGING, Action.NEUTRAL_B_FULL_CHARGE_AIR]:
                    return 6
                else:
                    return framedata.frame_count(opponent_state.character, opponent_state.action) - opponent_state.action_frame
            if attackstate == melee.enums.AttackState.ATTACKING and smashbro_state.action != Action.SHIELD_RELEASE:
                return 0
            if attackstate == melee.enums.AttackState.COOLDOWN:
                frame = framedata.iasa(opponent_state.character, opponent_state.action)
                return max(0, frame - opponent_state.action_frame)

        # for sharking
        if opponent_state.jumps_left == 0:
            if opponent_state.position.y > .02 or not opponent_state.on_ground:
                # When will they land?
                speed = opponent_state.speed_y_attack + opponent_state.speed_y_self
                height = opponent_state.position.y
                gravity = framedata.characterdata[opponent_state.character]["Gravity"]
                termvelocity = framedata.characterdata[opponent_state.character]["TerminalVelocity"]
                count = 0
                while height > 0:
                    height += speed
                    speed -= gravity
                    speed = max(speed, -termvelocity)
                    count += 1
                    # Shortcut if we get too far
                    if count > 120:
                        break
                return count
            return 0

        if framedata.is_roll(opponent_state.character, opponent_state.action):
            frame = framedata.last_roll_frame(opponent_state.character, opponent_state.action)
            return max(0, frame - opponent_state.action_frame)

        # Opponent is in hitstun
        if opponent_state.hitstun_frames_left > 0:
            # Special case here for lying on the ground.
            #   For some reason, the hitstun count is totally wrong for these actions
            if opponent_state.action in [Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN]:
                return 1

            # If opponent is in the air, we need to cap the return at when they will hit the ground
            if opponent_state.position.y > .02 or not opponent_state.on_ground:
                # When will they land?
                speed = opponent_state.speed_y_attack + opponent_state.speed_y_self
                height = opponent_state.position.y
                gravity = framedata.characterdata[opponent_state.character]["Gravity"]
                termvelocity = framedata.characterdata[opponent_state.character]["TerminalVelocity"]
                count = 0
                while height > 0:
                    height += speed
                    speed -= gravity
                    speed = max(speed, -termvelocity)
                    count += 1
                    # Shortcut if we get too far
                    if count > 120:
                        break
                return min(count, opponent_state.hitstun_frames_left)

            return opponent_state.hitstun_frames_left

        # Opponent is in a lag state
        if opponent_state.action in [Action.UAIR_LANDING, Action.FAIR_LANDING, \
                Action.DAIR_LANDING, Action.BAIR_LANDING, Action.NAIR_LANDING]:
            # TODO: DO an actual lookup to see how many frames this is
            return 8 - (opponent_state.action_frame // 3)

        # Exception for Jigglypuff rollout
        #   The action frames are weird for this action, and Jiggs is actionable during it in 1 frame
        if opponent_state.character == Character.JIGGLYPUFF and \
                opponent_state.action in [Action.SWORD_DANCE_1, Action.NEUTRAL_B_FULL_CHARGE_AIR, Action.SWORD_DANCE_4_LOW, \
                Action.SWORD_DANCE_4_MID, Action.SWORD_DANCE_3_LOW]:
            return 1

        # Opponent is in a B move
        if framedata.is_bmove(opponent_state.character, opponent_state.action):
            return framedata.frame_count(opponent_state.character, opponent_state.action) - opponent_state.action_frame

        return 1

    # given the current gamestate
    def canpunish(smashbro_state, opponent_state, gamestate, framedata):

        restingpuff = opponent_state.character == Character.JIGGLYPUFF and opponent_state.action == Action.MARTH_COUNTER
        if restingpuff or opponent_state.action in [Action.SHIELD_BREAK_TEETER, Action.SHIELD_BREAK_STAND_U]:
            return True

        # Wait until the later shieldbreak animations to punish, sometimes SmashBro usmashes too early
        if opponent_state.action in [Action.SHIELD_BREAK_FLY, Action.SHIELD_BREAK_DOWN_U]:
            return False

        # Can't punish opponent in shield
        shieldactions = [Action.SHIELD_START, Action.SHIELD, Action.SHIELD_RELEASE, \
            Action.SHIELD_STUN, Action.SHIELD_REFLECT]
        if opponent_state.action in shieldactions:
            return False

        if smashbro_state.off_stage or opponent_state.off_stage:
            return False

        # marth deadfall
        marth_fall = opponent_state.character in [Character.MARTH] and opponent_state.action in [Action.UP_B_GROUND]
        if (opponent_state.action in [Action.DEAD_FALL] or marth_fall) and not opponent_state.off_stage:
            return True

        if opponent_state.action in [Action.EDGE_JUMP_1_QUICK, Action.EDGE_JUMP_2_QUICK,
                                     Action.EDGE_JUMP_1_SLOW, Action.EDGE_JUMP_2_SLOW]:
            return True

        firefox = opponent_state.action == Action.SWORD_DANCE_3_LOW and opponent_state.character in [Character.FOX, Character.FALCO]
        if firefox and opponent_state.position.y > 15:
            return False

        left = Punish.framesleft(opponent_state, framedata, smashbro_state)
        # Will our opponent be invulnerable for the entire punishable window?
        if left <= opponent_state.invulnerability_left:
            return False

        if left < 1:
            return False

        if framedata.is_roll(opponent_state.character, opponent_state.action):
            return True

        # Don't punish if the vertical difference is too great.
        if abs(smashbro_state.position.y - opponent_state.position.y) > 10:
            return False

        return False

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate = (gamestate, smashbro_state, opponent_state)

        # Can we charge an upsmash right now?
        framesleft = Punish.framesleft(opponent_state, self.framedata, smashbro_state)

        endposition = opponent_state.position.x + self.framedata.slide_distance(opponent_state, opponent_state.speed_ground_x_self, 7)
        ourendposition = smashbro_state.position.x + self.framedata.slide_distance(smashbro_state, smashbro_state.speed_ground_x_self, 7)
        # grab range
        ingrabrange = abs(endposition - ourendposition) < 23 # normally 14.5, but this accounts for boostgrab

        if self.logger:
            self.logger.log("Notes", "framesleft: " + str(framesleft) + " ", concat=True)

        #If we can't interrupt the chain, just continue it
        if self.chain != None and not self.chain.interruptible:
            self.chain.step(gamestate, smashbro_state, opponent_state)
            return

        # TODO: May be missing some relevant inactionable states
        inactionablestates = [Action.THROW_DOWN, Action.THROW_UP, Action.THROW_FORWARD, Action.THROW_BACK, Action.UAIR_LANDING, Action.FAIR_LANDING, \
                Action.DAIR_LANDING, Action.BAIR_LANDING, Action.NAIR_LANDING, Action.UPTILT, Action.DOWNTILT, Action.UPSMASH, \
                Action.DOWNSMASH, Action.FSMASH_MID, Action.FTILT_MID, Action.FTILT_LOW, Action.FTILT_HIGH]
        if smashbro_state.action in inactionablestates:
            self.pickchain(Chains.Nothing)
            return

        # Attempt powershield action, note, we don't have a way of knowing for sure if we hit a physical PS
        opponentxvelocity = (opponent_state.speed_air_x_self + opponent_state.speed_ground_x_self + opponent_state.speed_x_attack)
        opponentyvelocity = (opponent_state.speed_y_attack + opponent_state.speed_y_self)
        opponentonright = opponent_state.position.x > smashbro_state.position.x

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

        laser_taken = gamestate.custom["laser_taken"]
        if laser_taken:
            print('laser taken, punish is possible, frames left:', framesleft)

        # for tournament winners
        # Check each height level, can we do an up-air right now?
        if opponent_state.action in [Action.EDGE_JUMP_1_QUICK, Action.EDGE_JUMP_2_QUICK, Action.EDGE_JUMP_1_SLOW, Action.EDGE_JUMP_2_SLOW]:
            if gamestate.distance < 15:
                self.chain = None
                tw_rng = random.randint(0, 1)
                if tw_rng == 0:
                    self.pickchain(Chains.AirAttack, [0, 0, 3, AIR_ATTACK_DIRECTION.FORWARD])
                    return
                else:
                    self.pickchain(Chains.AirAttack, [0, 0, 3, AIR_ATTACK_DIRECTION.NEUTRAL])
                    return

        shieldactions = [Action.SHIELD_START, Action.SHIELD, Action.SHIELD_RELEASE, Action.SHIELD_STUN, Action.SHIELD_REFLECT]

        if framesleft <= 30: # was 10 before
            # If opponent is on a side platform and we're not
            on_main_platform = smashbro_state.position.y < 1 and smashbro_state.on_ground
            if opponent_state.position.y > 1 and opponent_state.on_ground and on_main_platform and gamestate.stage != melee.enums.Stage.FOUNTAIN_OF_DREAMS:
                self.pickchain(Chains.BoardSidePlatform, [opponent_state.position.x > 0])
                # print('punish board side platform')
                return

        # How many frames needed to do a thing?
        framesneeded = 0
        runningactions = [Action.DASHING, Action.RUNNING]
        if smashbro_state.action in shieldactions:
            framesneeded += 1
        if smashbro_state.action in runningactions:
            framesneeded += 1

        opoutside = abs(smashbro_state.position.x) < abs(opponent_state.position.x)
        endposition = opponent_state.position.x
        isroll = self.framedata.is_roll(opponent_state.character, opponent_state.action)
        slideoff = False

        # If we have the time....
        if framesneeded <= framesleft:
            # opening finder
            # if framesleft > 0:
            #     print('opening found:', framesleft - framesneeded, opponent_state.action)

            # Calculate where the opponent will end up
            if opponent_state.hitstun_frames_left > 0:
                endposition = opponent_state.position.x + self.framedata.slide_distance(opponent_state, opponent_state.speed_x_attack, framesleft)

            if isroll:
                endposition = self.framedata.roll_end_position(opponent_state, gamestate.stage)

                initialrollmovement = 0
                facingchanged = False
                try:
                    initialrollmovement = self.framedata.framedata[opponent_state.character][opponent_state.action][opponent_state.action_frame]["locomotion_x"]
                    facingchanged = self.framedata.framedata[opponent_state.character][opponent_state.action][opponent_state.action_frame]["facing_changed"]
                except KeyError:
                    pass
                backroll = opponent_state.action in [Action.ROLL_BACKWARD, Action.GROUND_ROLL_BACKWARD_UP, \
                    Action.GROUND_ROLL_BACKWARD_DOWN, Action.BACKWARD_TECH]
                if not (opponent_state.facing ^ facingchanged ^ backroll):
                    initialrollmovement = -initialrollmovement

                speed = opponent_state.speed_x_attack + opponent_state.speed_ground_x_self - initialrollmovement
                endposition += self.framedata.slide_distance(opponent_state, speed, framesleft)

                # But don't go off the end of the stage
                if opponent_state.action in [Action.TECH_MISS_DOWN, Action.TECH_MISS_UP, Action.NEUTRAL_TECH]:
                    if abs(endposition) > melee.stages.EDGE_GROUND_POSITION[gamestate.stage]:
                        slideoff = True
                endposition = max(endposition, -melee.stages.EDGE_GROUND_POSITION[gamestate.stage])
                endposition = min(endposition, melee.stages.EDGE_GROUND_POSITION[gamestate.stage])

            # And we're in range...
            # Take our sliding into account
            slidedistance = self.framedata.slide_distance(smashbro_state, smashbro_state.speed_ground_x_self, framesleft)
            smashbro_endposition = slidedistance + smashbro_state.position.x

            # Do we have to consider character pushing?
            # Are we between the character's current and predicted position?
            if opponent_state.position.x < smashbro_endposition < endposition or \
                    opponent_state.position.x > smashbro_endposition > endposition:
                # Add a little bit of push distance along that path
                # 0.3 pushing for max of 16 frames
                onleft = smashbro_state.position.x < opponent_state.position.x
                if onleft:
                    smashbro_endposition -= 4.8
                else:
                    smashbro_endposition += 4.8

            if self.logger:
                self.logger.log("Notes", "endposition: " + str(endposition) + " ", concat=True)
                self.logger.log("Notes", "smashbro_endposition: " + str(smashbro_endposition) + " ", concat=True)

            facing = smashbro_state.facing == (smashbro_endposition < endposition)
            # Remember that if we're turning, the attack will come out the opposite way
            # On f1 of smashturn, smashbro hasn't changed directions yet. On/after frame 2, it has. Tilt turn may be a problem.
            if smashbro_state.action == Action.TURNING and smashbro_state.action_frame == 1:
                facing = not facing

            # Get height of opponent at the targeted frame
            height = opponent_state.position.y
            firefox = opponent_state.action == Action.SWORD_DANCE_3_LOW and opponent_state.character in [Character.FOX, Character.FALCO]
            speed = opponent_state.speed_y_attack
            gravity = self.framedata.characterdata[opponent_state.character]["Gravity"]
            termvelocity = self.framedata.characterdata[opponent_state.character]["TerminalVelocity"]
            if not opponent_state.on_ground and not firefox:
                # Loop through each frame and count the distances
                for i in range(framesleft):
                    speed -= gravity
                    # We can't go faster than termvelocity downwards
                    speed = max(speed, -termvelocity)
                    height += speed

            distance = abs(endposition - smashbro_endposition)
            x = 1
            # If we are really close to the edge, wavedash straight down
            if melee.stages.EDGE_GROUND_POSITION[gamestate.stage] - abs(smashbro_state.position.x) < 3:
                x = 0
            # This makes SmashBro wavedash down near the ledge.
            if abs(opponent_state.position.x) + 41 > melee.stages.EDGE_GROUND_POSITION[gamestate.stage] and abs(opponent_state.position.x) > abs(smashbro_state.position.x):
                x = 0

            diff_x = abs(smashbro_state.position.x - opponent_state.position.x)
            diff_y = abs(smashbro_state.position.y - opponent_state.position.y)

            techmiss = [Action.TECH_MISS_UP, Action.TECH_MISS_DOWN, Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN]

            # ground options:
            # grab, 7/30 or 8/40,
            # tilt, 5/28, mid % and close
            # dsmash, 5/46, close and fastfaller
            # dash, 6/36, high % and far
            # usmash, 12/40, high % for floaty
            # nair, 6/?, high % and close

            # air options:
            # fair, 5/33, close-catchall
            # bair, 4/37, far and low % or at high %
            # nair, 3/48, falling or at high %
            # dair, 15/48, high %

            # regular getup, tech in place, tech miss
            # tech-chasing rolls
            if isroll and distance < 30 and smashbro_state.on_ground and opponent_state.on_ground:
                self.chain = None
                # tech-chase finishers
                if opponent_state.percent > 130 or (opponent_state.percent > 100 and floaty):
                    if distance < 5 and framesleft - framesneeded <= 12:
                        self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.UP])
                        if smashbro_state.action_frame == 1:
                            print("tech-chase usmash")
                        return
                if opponent_state.percent > 130 or (opponent_state.percent > 100 and opoutside):
                    if "up" not in gamestate.custom["predominant_SDI_direction"] and fastfaller:
                        if distance < 20 and framesleft - framesneeded <= 5:
                            if smashbro_state.action in [Action.STANDING]:
                                self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                                if smashbro_state.action_frame == 1:
                                    print('tech-chase dsmash')
                                return
                if opponent_state.percent > 90 and floaty:
                    if distance < 15 and facing and framesleft - framesneeded <= 2:
                        if smashbro_state.action in [Action.STANDING, Action.TURNING]:
                            self.pickchain(Chains.Jab)
                            if smashbro_state.action_frame == 1:
                                print('tech-chase jab')
                            return
                if opponent_state.percent > 75:
                    if framesleft - framesneeded <= 6:
                        if smashbro_state.action in [Action.STANDING, Action.TURNING] and facing:
                            if distance < 15 and facing and floaty:
                                self.pickchain(Chains.Jab)
                                if smashbro_state.action_frame == 1:
                                    print('tech-chase jab')
                                return
                        if 15 < diff_x < 25 and facing:
                            if smashbro_state.action in [Action.DASHING, Action.RUNNING]:
                                self.pickchain(Chains.DashAttack)
                                if smashbro_state.action_frame == 1:
                                    print('tech-chase dash attack')
                                return
                # tech miss
                if opponent_state.action in techmiss and distance < 15:
                    if opponent_state.percent < 120:
                        if (floaty and opponent_state.percent < 60) or fastfaller:
                            if smashbro_state.action in [Action.STANDING] and facing:
                                self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                                if smashbro_state.action_frame == 1:
                                    print('tech-chase ftilt')
                                return
                        if smashbro_state.action in [Action.STANDING, Action.TURNING]:
                            if distance < 10 and facing:
                                self.pickchain(Chains.Jab)
                                if smashbro_state.action_frame == 1:
                                    print('tech-chase jab')
                                return
                            if distance > 8 and not facing:
                                self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                                if smashbro_state.action_frame == 1:
                                    print('tech-chase dsmash')
                                return
                            else:
                                self.pickchain(Chains.Tilt, [TILT_DIRECTION.UP])
                                if smashbro_state.action_frame == 1:
                                    print('tech-chase utilt')
                                return
                    if facing and smashbro_state.on_ground:
                        if smashbro_state.action in [Action.STANDING] \
                                or (smashbro_state.action in [Action.RUNNING] and distance > 7):
                            self.pickchain(Chains.Crouchcancel, [1])
                            if smashbro_state.action_frame == 1:
                                print('tech-chase crouch cancel called')
                            return
                    if smashbro_state.on_ground:
                        self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                        if smashbro_state.action_frame == 1:
                            print('tech-chase dsmash')
                        return
                # escapable
                if 3 < framesleft - framesneeded < 8 and diff_y < 9 and facing:
                    self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                    if smashbro_state.action_frame == 1:
                        print('tech-chase dthrow, escape window:', framesleft - 6)
                    return
                else:
                    self.pickchain(Chains.ExactDash, [endposition, 0, False])
                    return

            # in range, non tech-chase
            if not slideoff and distance < 30 and diff_y < 9:
                # If Chic is within 20 units of the edge
                self.chain = None
                if abs(smashbro_state.position.x) + 20 > melee.stages.EDGE_GROUND_POSITION[gamestate.stage]:
                    # TODO add dshffl to zone at edge
                    if not facing and opoutside:
                        self.pickchain(Chains.Dshffl, [DSHFFL_DIRECTION.BACK])
                        if smashbro_state.action_frame == 1:
                            print('punish edge dshffl bair')
                        return
                    if ingrabrange and facing and framesleft - framesneeded < 7 and smashbro_state.on_ground and \
                            opponent_state.action not in [Action.LYING_GROUND_UP, Action.LYING_GROUND_DOWN]:
                        self.pickchain(Chains.GrabAndThrow, [THROW_DIRECTION.DOWN])
                        if smashbro_state.action_frame == 1:
                            print('punish dthrow')
                        return
                    if facing and smashbro_state.action in [Action.STANDING, Action.TURNING]:
                        if diff_x < 10 and floaty and 20 < opponent_state.percent < 60 or not opponent_state.on_ground \
                                and smashbro_state.action in [Action.STANDING]:
                            self.pickchain(Chains.Tilt, [TILT_DIRECTION.DOWN])
                            if smashbro_state.action_frame == 1:
                                print('punish dtilt')
                            return
                        if distance < 15 and opponent_state.percent > 80:
                            self.pickchain(Chains.Jab)
                            if smashbro_state.action_frame == 1:
                                print('punish jab')
                            return
                        if opponent_state.percent < 60:
                            self.pickchain(Chains.Tilt, [TILT_DIRECTION.FORWARD])
                            if smashbro_state.action_frame == 1:
                                print('punish ftilt')
                            return
                if opponent_state.percent < 20 or opponent_state.percent > 60:
                    if smashbro_state.on_ground:
                        if 15 < distance < 25 and 60 < opponent_state.percent < 90 and facing:
                            self.pickchain(Chains.DashAttack)
                            if smashbro_state.action_frame == 1:
                                print('punish dash attack')
                            return
                        if fastfaller and (opponent_state.percent > 80 or "down" in gamestate.custom["predominant_SDI_direction"]) \
                                and distance < 20 and smashbro_state.action != Action.RUNNING:
                            self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                            print('punish dsmash')
                            return
            # If we're not in attack range, and can't run, then maybe we can wavedash in
            #   Now we need more time for the wavedash. 10 frames of lag, and 3 jumping
            framesneeded = 13
            if framesneeded <= framesleft:
                if smashbro_state.action in shieldactions:
                    self.pickchain(Chains.Wavedash, [True])
                    return

        # smashbro falling on
        if smashbro_state.speed_y_self < 0:
            if facing and (opponent_state.percent > 25 or opponent_state.on_ground):
                if 0 < opponent_state.position.y < 10:
                    self.pickchain(Chains.Dshffl, [DSHFFL_DIRECTION.FORWARD])
                    if smashbro_state.action_frame == 1:
                        print('punish dshffl fair')
                    return
                else:
                    self.pickchain(Chains.FallingAerial, [AIR_ATTACK_DIRECTION.FORWARD])
                    if smashbro_state.action_frame == 1:
                        print('punish falling fair')
                    return

        # Kill the existing chain and start a new one
        self.chain = None
        self.pickchain(Chains.DashDance, [endposition])
