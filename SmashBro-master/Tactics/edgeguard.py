import melee
import Chains
import math
import random
from melee.enums import Action, Button, Character
from Tactics.tactic import Tactic
from Tactics.punish import Punish
from Tactics.defend import Defend
from Chains.smashattack import SMASH_DIRECTION
from Chains.airattack import AirAttack, AIR_ATTACK_DIRECTION
from Chains.dropaerial import DropAerial, DROP_AERIAL_DIRECTION
from Chains.tilt import TILT_DIRECTION
from Chains.shffl import SHFFL_DIRECTION
from Chains.dshffl import DSHFFL_DIRECTION
from Chains.edgeaerial import EdgeAerial, EDGE_AERIAL_DIRECTION


class Edgeguard(Tactic):
    def __init__(self, logger, controller, framedata, difficulty):
        Tactic.__init__(self, logger, controller, framedata, difficulty)
        self.upbstart = 0

    # This is exactly flipped from the recover logic
    def canedgeguard(smashbro_state, opponent_state, gamestate):
        if not smashbro_state.off_stage and opponent_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]:
            return True

        if not opponent_state.off_stage:
            return False

        # duct tape to stop from committing self die (Sheik specific)
        if smashbro_state.position.y < -80:
            return False

        # We can now assume that opponent is off the stage...

        # If smashbro is on stage
        if not smashbro_state.off_stage:
            return True

        # If smashbro is fully off the stage, then don't start an edge guard
        if smashbro_state.off_stage and not smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]:
            return False

        if smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]:
            return True

        # If smashbro is in hitstun, then recover
        if smashbro_state.off_stage and smashbro_state.hitstun_frames_left > 0:
            return False

        # Steal the ledge from Sheik Shino stall
        if opponent_state.character == Character.SHEIK and opponent_state.action == Action.SWORD_DANCE_1_AIR and opponent_state.action_frame < 5:
            return True

        # If smashbro is closer to the edge, edgeguard
        diff_x_opponent = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(opponent_state.position.x))
        diff_x = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(smashbro_state.position.x))

        opponentonedge = opponent_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]

        opponent_dist = math.sqrt( (opponent_state.position.y+15)**2 + (diff_x_opponent)**2 )
        smashbro_dist = math.sqrt( (smashbro_state.position.y+15)**2 + (diff_x)**2 )

        if smashbro_dist < opponent_dist and not opponentonedge:
            return True

        return False

    def illusionhighframes(self, gamestate, opponent_state):
        inillusion =  opponent_state.character in [Character.FOX, Character.FALCO] and \
            opponent_state.action in [Action.SWORD_DANCE_2_HIGH, Action.SWORD_DANCE_2_MID] and (0 < opponent_state.position.y < 30)
        if not inillusion:
            return 999
        if not (-2 < opponent_state.position.y < 25):
            return 999

        edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        if opponent_state.position.x < 0:
            edge_x = -edge_x

        speed = 16.5
        if opponent_state.character == Character.FOX:
            speed = 18.72

        if opponent_state.position.x > 0:
            speed = -speed

        x = opponent_state.position.x
        frames = 0
        for i in range(1, 3):
            x += speed
            if abs(edge_x - x) < 10:
                frames = i

        if frames == 0:
            return 999

        # Plus the windup frames
        if opponent_state.action == Action.SWORD_DANCE_2_HIGH:
            frames += self.framedata.frame_count(opponent_state.character, opponent_state.action) - opponent_state.action_frame + 1

        return frames

    # Is opponent trying to firefox above the stage?
    def firefoxhighframes(self, gamestate, opponent_state):
        firefox = opponent_state.action in [Action.SWORD_DANCE_4_HIGH, Action.SWORD_DANCE_4_MID] and opponent_state.character in [Character.FOX, Character.FALCO]
        if not firefox:
            return 999

        edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        if opponent_state.position.x < 0:
            edge_x = -edge_x

        x, y = opponent_state.position.x, opponent_state.position.y
        # Project their trajectory. Does it reach right above the edge? When will it?
        for i in range(self.framedata.frame_count(opponent_state.character, opponent_state.action) - opponent_state.action_frame):
            x += opponent_state.speed_air_x_self
            y += opponent_state.speed_y_self
            if abs(edge_x - x) < 10 and 0 < y < 25:
                return i

        return 999

    def dolphinslashhighframes(self, gamestate, opponent_state):
        dolphinslash = opponent_state.action in [Action.UP_B_AIR] and opponent_state.character in [Character.MARTH]
        if not dolphinslash:
            return 999

        edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        if opponent_state.position.x < 0:
            edge_x = -edge_x

        x, y = opponent_state.position.x, opponent_state.position.y
        for i in range(self.framedata.frame_count(opponent_state.character, opponent_state.action) - opponent_state.action_frame):
            x += opponent_state.speed_air_x_self
            y += opponent_state.speed_y_self
            if abs(edge_x - x) < 10 and 0 < y < 25:
                return i

        return 999

    def canrecoverhigh(self, gamestate, opponent_state):
        if opponent_state.character in [Character.JIGGLYPUFF, Character.PIKACHU]:
            return True

        # Don't grab the edge if opponent is recovering high.
        #   Let's define that as: If the opponent can get onto the stage (not edge)
        #   with only a jump, without crossing the 0 Y line

        # How long will it take for opponent to reach the edge horizontally?
        frames_x = 0
        gravity = self.framedata.characterdata[opponent_state.character]["Gravity"]
        termvelocity = self.framedata.characterdata[opponent_state.character]["TerminalVelocity"]
        mobility = self.framedata.characterdata[opponent_state.character]["AirMobility"]
        airspeed = self.framedata.characterdata[opponent_state.character]["AirSpeed"]
        initialdjspeed_y = self.framedata.characterdata[opponent_state.character]["InitDJSpeed"]
        initialdjspeed_x = self.framedata.characterdata[opponent_state.character]["InitDJSpeed_x"]

        # Marth has side-b, which effectively decreases his gravity for this calculation
        if opponent_state.character == Character.MARTH:
            gravity = gravity / 2
        # Samus has bomb jumps, which gives her almost infinite horizontal recovery
        if opponent_state.character == Character.SAMUS:
            gravity = gravity / 4

        speed_x = opponent_state.speed_air_x_self + opponent_state.speed_x_attack
        speed_y = opponent_state.speed_y_self + opponent_state.speed_y_attack

        x, y = opponent_state.position.x, opponent_state.position.y

        if x > 0:
            mobility = -mobility

        # If they have a jump, assume they will use it
        if opponent_state.jumps_left > 0:
            speed_y = initialdjspeed_y
            if x > 0:
                speed_x = -initialdjspeed_x
            else:
                speed_x = initialdjspeed_x

        edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]

        # Move opponent frame by frame back to the edge. Do they get past it? Or fall below?
        while abs(x) > edge_x:
            y += speed_y
            speed_y -= gravity
            speed_y = max(-termvelocity, speed_y)

            x += speed_x
            speed_x += mobility
            speed_x = max(-airspeed, speed_x)
            speed_x = min(airspeed, speed_x)

        # If they are below 0, then opponent can't recover high with a jump
        if y < 0:
            return False

        return True

    def upbheight(self, opponent_state):
        character = opponent_state.character

        if character == Character.FOX:
            # If they are in the teleport section, predict how much more they have to go
            if opponent_state.action in [Action.SWORD_DANCE_4_MID, Action.SWORD_DANCE_1_AIR]:
                c = math.sqrt(opponent_state.speed_y_self**2 + opponent_state.speed_air_x_self**2)
                height = (opponent_state.speed_y_self / c) * 81.5
                return height
            return 84.55
        if character == Character.FALCO:
            # If they are in the teleport section, predict how much more they have to go
            if opponent_state.action in [Action.SWORD_DANCE_4_MID, Action.SWORD_DANCE_1_AIR]:
                c = math.sqrt(opponent_state.speed_y_self**2 + opponent_state.speed_air_x_self**2)
                height = (opponent_state.speed_y_self / c) * 61.5
                return height
            return 62.4
        if character == Character.CPTFALCON:
            return 37.62
        if character == Character.MARTH:
            return 50.72
        # Just remember that he gets two of them
        if character == Character.PIKACHU:
            return 54.39
        if character == Character.JIGGLYPUFF:
            return 0
        if character == Character.PEACH:
            return 28.96
        if character == Character.ZELDA:
            return 70.412
        if character == Character.SHEIK:
            return 69.632
        if character == Character.SAMUS:
            return 46.1019

        # This is maybe average, in case we get here
        return 40

    def upbapexframes(self, opponent_state):
        character = opponent_state.character
        if character == Character.FOX:
            return 118
        if character == Character.FALCO:
            return 70
        if character == Character.CPTFALCON:
            return 45
        if character == Character.MARTH:
            return 23
        # Just remember that he gets two of them
        if character == Character.PIKACHU:
            return 30
        if character == Character.JIGGLYPUFF:
            return 0
        if character == Character.PEACH:
            return 34
        if character == Character.ZELDA:
            return 73
        # Sheik's up-b is dumb, and has TWO points where it can grab the edge. Ugh
        #   This just counts the first
        if character == Character.SHEIK:
            return 19
        if character == Character.SAMUS:
            return 38

        # This is maybe average, in case we get here
        return 40

    # This is the very lazy way of doing this, but "meh". Maybe I'll get around to doing it right
    def isupb(self, opponent_state):
        character = opponent_state.character
        action = opponent_state.action
        if character in [Character.FOX, Character.FALCO]:
            if action in [Action.SWORD_DANCE_3_LOW, Action.SWORD_DANCE_4_MID, Action.SWORD_DANCE_1_AIR]:
                return True
        if character == Character.CPTFALCON:
            if action in [Action.SWORD_DANCE_3_LOW]:
                return True
        if character == Character.MARTH:
            if action in [Action.SHINE_RELEASE_AIR]:
                return True
        # Just remember that he gets two of them
        if character == Character.PIKACHU:
            if action in [Action.SWORD_DANCE_4_MID, Action.SWORD_DANCE_4_LOW, Action.SWORD_DANCE_1_AIR]:
                return True
        if character == Character.JIGGLYPUFF:
            return False
        if character == Character.PEACH:
            if action in [Action.SWORD_DANCE_3_LOW_AIR, Action.PARASOL_FALLING, Action.MARTH_COUNTER]:
                return True
        if character == Character.ZELDA:
            if action in [Action.SWORD_DANCE_3_HIGH, Action.SWORD_DANCE_3_MID, Action.SWORD_DANCE_3_LOW]:
                return True
        if character == Character.SHEIK:
            if action in [Action.SWORD_DANCE_1_AIR, Action.SWORD_DANCE_2_HIGH_AIR, Action.SWORD_DANCE_2_MID_AIR]:
                return True
        if character == Character.SAMUS:
            if action in [Action.SWORD_DANCE_3_LOW]:
                return True
        return False

    def snaptoedgeframes(self, gamestate, opponent_state):
        # How long will it take opponent to grab the edge?
        #   Distance to the snap point of the edge
        edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
        edgedistance = abs(opponent_state.position.x) - (edge_x + 15)
        # Assume opponent can move at their "max" speed
        airhorizspeed = self.framedata.characterdata[opponent_state.character]["AirSpeed"]
        edgegrabframes_x = edgedistance // airhorizspeed
        fastfallspeed = self.framedata.characterdata[opponent_state.character]["FastFallSpeed"]

        # Samus can grapple, making all the math below wrong
        if opponent_state.action == Action.SWORD_DANCE_1_AIR and opponent_state.character == Character.SAMUS:
            return 1

        # Can opponent get to the vertical snap position in time?
        #   This is the shortest possible time opponent could get into position
        edgegrabframes_y = 1000
        # Are they already in place?
        if -5 > opponent_state.position.y > -23:
            edgegrabframes_y = 0
        # Are they above?
        elif opponent_state.position.y > -5:
            edgegrabframes_y = (opponent_state.position.y + 5) // fastfallspeed
        # Are they below?
        elif opponent_state.position.y < -23:
            djapexframes = self.framedata.frames_until_dj_apex(opponent_state)
            djheight = self.framedata.dj_height(opponent_state)
            # Can they double-jump to grab the edge?
            if -5 > opponent_state.position.y + djheight > -23:
                edgegrabframes_y = djapexframes
            elif opponent_state.position.y + djheight > -5:
                # If the jump puts them too high, then we have to wait for them to fall after the jump
                fallframes = (opponent_state.position.y + djheight + 5) // fastfallspeed
                edgegrabframes_y = djapexframes + fallframes
            elif opponent_state.position.y + djheight < -23:
                # If the jump puts them too low, then they have to UP-B. How long will that take?
                upbframes = self.upbapexframes(opponent_state)
                edgegrabframes_y = upbframes
                # How many falling frames do they need?
                fallframes = (opponent_state.position.y + upbframes + 5) // fastfallspeed
                if fallframes > 0:
                    edgegrabframes_y += fallframes

        edgegrabframes = max(edgegrabframes_x, edgegrabframes_y)

        facinginwards = opponent_state.facing == (opponent_state.position.x < 0)
        firefox = opponent_state.character in [Character.FOX, Character.FALCO] and \
            opponent_state.action == Action.SWORD_DANCE_3_LOW and facinginwards
        inteleport = opponent_state.character in [Character.FOX, Character.FALCO] and \
            opponent_state.action == Action.SWORD_DANCE_4_MID


        falconupbstart = opponent_state.character == Character.CPTFALCON and \
            opponent_state.action == Action.SWORD_DANCE_3_LOW and opponent_state.action_frame <= 44
        if falconupbstart:
            edgegrabframes = max(44 - opponent_state.action_frame, 0)

        # Teleport exceptions here
        #   Some characters have "teleport" moves. Sheik, Zelda, Fox, Falco, etc...
        #   Teleport moves have a startup, then you move at a set speed at any angle
        #   In these cases, opponent COULD grab the edge much faster than in other situations
        if opponent_state.character in [Character.SHEIK, Character.ZELDA, Character.FOX, Character.FALCO, \
                Character.PIKACHU, Character.PICHU, Character.MEWTWO]:
            if opponent_state.position.y > 0 and opponent_state.action != Action.DEAD_FALL:
                edgegrabframes = 1
                if firefox:
                    edgegrabframes = max(15 - opponent_state.action_frame, 0)
            # If in place to grab edge,
            if (-5 > opponent_state.position.y > -23) and firefox:
                edgegrabframes = max(15 - opponent_state.action_frame, 0)
            # If opponent is IN the teleport phase, then it matters whether they're moving up or down
            if inteleport:
                if opponent_state.speed_y_self > 0:
                    edgegrabframes = self.framedata.frame_count(opponent_state.character, opponent_state.action) - opponent_state.action_frame
                else:
                    edgegrabframes = 0

            # Pichu and Pikachu get two teleports, so just always consider them active to grab the edge
            if opponent_state.character in [Character.PIKACHU, Character.PICHU]:
                edgegrabframes = 1
        return edgegrabframes

    def step(self, gamestate, smashbro_state, opponent_state):
        self._propagate  = (gamestate, smashbro_state, opponent_state)

        recoverhigh = self.canrecoverhigh(gamestate, opponent_state)

        # fIf we can't interrupt the chain, just continue it
        if self.chain != None and not self.chain.interruptible:
            self.chain.step(gamestate, smashbro_state, opponent_state)
            return

        if smashbro_state.action == Action.EDGE_CATCHING:
            self.pickchain(Chains.Nothing)
            return

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

        diff_x_opponent = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(opponent_state.position.x))
        diff_x = abs(melee.stages.EDGE_POSITION[gamestate.stage] - abs(smashbro_state.position.x))
        facinginwards = opponent_state.facing == (opponent_state.position.x < 0)

        opoutside = abs(smashbro_state.position.x) < abs(opponent_state.position.x)

        # How many frames will it take to get to our opponent right now?
        onedge = smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]

        # >>
        # What recovery options does opponent have?
        landonstage = False
        grabedge = False
        # they have to commit to an up-b to recover
        mustupb = False
        canrecover = True

        djheight = self.framedata.dj_height(opponent_state)

        edgegrabframes = self.snaptoedgeframes(gamestate, opponent_state)

        # How high can they go with a jump?
        potentialheight = djheight + opponent_state.position.y
        if potentialheight < -23:
            mustupb = True

        # Now consider UP-B
        #   Have they already UP-B'd?
        if self.isupb(opponent_state):
            if self.upbstart == 0:
                self.upbstart = opponent_state.position.y
            # If they are halfway through the up-b, then subtract out what they've already used
            potentialheight = self.upbheight(opponent_state) + self.upbstart
        elif opponent_state.action == Action.DEAD_FALL:
            potentialheight = opponent_state.position.y
        else:
            potentialheight += self.upbheight(opponent_state)

        # Cpt Falcon's up-b causes him to distort his model by a crazy amount. Giving him
        #   the ability to get on the stage easier. Adjust for this
        adjustedheight = potentialheight
        if opponent_state.character == Character.CPTFALCON and self.isupb(opponent_state):
            adjustedheight += 12

        # Adjust upwards a little to have some wiggle room
        if adjustedheight > -5:
            landonstage = True
        if potentialheight > -23:
            grabedge = True
        if potentialheight < -30:
            mustupb = True
            canrecover = False

        # Stand up if opponent attacks us
        proj_incoming = Defend.needsprojectiledefense(smashbro_state, opponent_state, gamestate) and smashbro_state.invulnerability_left <= 2

        samusgrapple = opponent_state.character == Character.SAMUS and opponent_state.action == Action.SWORD_DANCE_4_LOW and \
            -25 < opponent_state.position.y < 0 and smashbro_state.invulnerability_left <= 2

        hitframe = self.framedata.in_range(opponent_state, smashbro_state, gamestate.stage)
        framesleft = hitframe - opponent_state.action_frame
        if proj_incoming or samusgrapple or (hitframe != 0 and onedge and framesleft < 5 and smashbro_state.invulnerability_left < 2):
            if not self.framedata.is_grab(opponent_state.character, opponent_state.action):
                if self.isupb(opponent_state):
                    # triggers immediately on up-b
                    if landonstage:
                        if smashbro_state.percent >= 100:
                            hp_rng = random.randint(0, 2)
                            if hp_rng == 0:
                                # spicy option
                                self.chain = None
                                self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.DOWN])
                                if smashbro_state.action_frame == 1:
                                    print('edgeguard dair')
                                return
                            else:
                                self.chain = None
                                x = 0.35
                                if smashbro_state.facing and smashbro_state.position.x < opponent_state.position.y:
                                    x = 0.65
                                self.controller.tilt_analog(Button.BUTTON_MAIN, x, .5)
                                return
                        # ledgedash if big overshoot
                        if adjustedheight > 15:
                            self.chain = None
                            self.pickchain(Chains.Edgedash, [False])
                            return
                        # TODO: cover opponent barely overshooting ledge, delayed fair, bair or nair
                        if adjustedheight > -5:
                            self.chain = None
                            self.pickchain(Chains.Edgehop, [False])
                            return
                    self.chain = None
                    self.controller.press_button(Button.BUTTON_L)  # roll up
                    return
                else:
                    self.chain = None
                    self.pickchain(Chains.DI, [0.5, 0.65])
                    return

        # For pikachu, we want to be up on the stage to edgeguard. Not on edge
        if opponent_state.character == Character.PIKACHU and smashbro_state.action == Action.EDGE_HANGING and smashbro_state.invulnerability_left == 0:
            if opponent_state.position.y < -20:
                self.chain = None
                self.pickchain(Chains.Edgedash, [False])
                return

        # Special exception for Fox/Falco illusion
        #   Since it is dumb and technically a projectile
        if opponent_state.character in [Character.FOX, Character.FALCO]:
            if opponent_state.action in [Action.SWORD_DANCE_2_MID]:
                self.chain = None
                self.pickchain(Chains.DI, [0.5, 0.65])
                return

        # >>

        # Split the logic into two:
        #   A) We are on the edge
        #   B) We are on the stage

        if smashbro_state.action in [Action.EDGE_HANGING, Action.EDGE_CATCHING]:
            # If opponent can't recover, then just get onto the stage!
            if not canrecover:
                self.chain = None
                self.controller.press_button(Button.BUTTON_L)
                return

            # Don't roll up too early for Falcon
            falconupearly = opponent_state.character == Character.CPTFALCON and \
                opponent_state.action == Action.SWORD_DANCE_3_LOW and opponent_state.action_frame <= 12

            # Roll up to edgehog, to fix
            if self.isupb(opponent_state) and not landonstage and not falconupearly:
                self.chain = None
                self.controller.press_button(Button.BUTTON_L)
                return

            # Challenge rising UP-B's if we're in range
            #   except for pikachu and falcon/ganon
            if self.isupb(opponent_state) and opponent_state.speed_y_self >= 0 and gamestate.distance < 10:
                # TODO add
                return

            # Samus UP_B invulnerability
            samusupbinvuln = opponent_state.action in [Action.SWORD_DANCE_3_MID, Action.SWORD_DANCE_3_LOW] and \
                             opponent_state.character == Character.SAMUS and opponent_state.action_frame <= 5

            # patrol space up to 17u above (strong hit at 0, ~8 frames to execute)
            # account for drift in and intercept
            if 23 < diff_x_opponent < 45 and 0 < opponent_state.position.y < 17 and diff_x < 50:
                self.pickchain(Chains.Edgereturnbairhigh)
                if smashbro_state.action_frame == 1:
                    print('edgeguard high bair')
                return

            # 7 frames
            if diff_x_opponent < 10 and -2 < opponent_state.position.y < 10:
                if opoutside:
                    if 5 < diff_x_opponent or opponent_state.percent > 150:  # 7 frames
                        self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.FORWARD])
                        if smashbro_state.action_frame == 1:
                            print('edgeguard fair')
                        return
                else:
                    if 20 < opponent_state.percent < 120:  # 17 frames, percent is filler
                        self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.DOWN])
                        if smashbro_state.action_frame == 1:
                            print('edgeguard dair')
                        return

            # TODO delayed reverse bair
            # patrol space up to 17u above
            if 5 < opponent_state.position.y < 17 and opoutside:
                if diff_x_opponent < 15:  # 5 frames
                    self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.NEUTRAL])
                    if smashbro_state.action_frame == 1:
                        print('edgeguard nair')
                    return
                if diff_x_opponent < 30:  # 7 frames
                    self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.BACK])
                    if smashbro_state.action_frame == 1:
                        print('edgeguard bair')
                    return

            # Drop aerial them, as long as they aren't attacking right now
            # this might result in a suicide on PS
            frameadvantage = framesleft > 2 or smashbro_state.invulnerability_left > 2
            if -50 < opponent_state.position.y < smashbro_state.position.y - 5 and not samusupbinvuln:
                if diff_x_opponent < 15 and opponent_state.position.y < -15:
                    if opponent_state.percent > 100 and diff_x_opponent < 3:
                        self.pickchain(Chains.DropAerial, [DROP_AERIAL_DIRECTION.NEUTRAL])
                        if smashbro_state.action_frame == 1:
                            print('edgeguard drop nair')
                        return
                if 20 < diff_x_opponent < 25 and opponent_state.position.y < -20 \
                        and abs(smashbro_state.position.x) < abs(opponent_state.position.x):
                    if opponent_state.character == Character.FOX:
                        # need to make sure we can get back to ledge before fox
                        if opponent_state.percent < 40 and opponent_state.position.y > -40:
                            self.pickchain(Chains.Edgereturnbairmid)
                            if smashbro_state.action_frame == 1:
                                print('edgeguard mid bair')
                            return
                        if opponent_state.percent > 80 or opponent_state.position.y > -75:
                            self.pickchain(Chains.DropAerial, [DROP_AERIAL_DIRECTION.BACK])
                            if smashbro_state.action_frame == 1:
                                print('edgeguard drop bair')
                            return
                    if heavy:
                        if opponent_state.percent > 80 and 10 < diff_x_opponent < 15:  # needs strong hit
                            self.pickchain(Chains.DropAerial, [DROP_AERIAL_DIRECTION.BACK])
                            if smashbro_state.action_frame == 1:
                                print('edgeguard drop bair')
                            return
                    else:
                        if opponent_state.percent > 60:
                            self.pickchain(Chains.DropAerial, [DROP_AERIAL_DIRECTION.BACK])
                            if smashbro_state.action_frame == 1:
                                print('edgeguard drop bair')
                            return

            # Edgestall
            # We must be on the first frame, or else it's dangerous
            if smashbro_state.action == Action.EDGE_HANGING and smashbro_state.action_frame == 1:
                if edgegrabframes > 29 and smashbro_state.invulnerability_left >= 29:
                    self.pickchain(Chains.Edgestall)
                    return

            framesleft = Punish.framesleft(opponent_state, self.framedata, smashbro_state)

            # Samus UP_B invulnerability
            samusupbinvuln = opponent_state.action in [Action.SWORD_DANCE_3_MID, Action.SWORD_DANCE_3_LOW] and \
                    opponent_state.character == Character.SAMUS and opponent_state.action_frame <= 5

            # Illusion high
            if self.illusionhighframes(gamestate, opponent_state) <= 5:
                if smashbro_state.invulnerability_left > 7:
                    self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.NEUTRAL])
                    return

            # If opponent is recovering high with illusion, nair them at the right time
            if (opponent_state.character == Character.FOX and opponent_state.action_frame == 15) or (opponent_state.character == Character.FALCO and opponent_state.action_frame == 10):
                if opponent_state.action == Action.SWORD_DANCE_2_HIGH and opponent_state.position.y > -4:
                    self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.NEUTRAL])
                    return

            # intercept firefoxes
            if self.firefoxhighframes(gamestate, opponent_state) <= 5:
                self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.NEUTRAL])
                return

            # intercept high dolphin slashes
            if self.dolphinslashhighframes(gamestate, opponent_state) <= 5:
                self.pickchain(Chains.EdgeAerial, [EDGE_AERIAL_DIRECTION.NEUTRAL])
                return

            # Do nothing
            self.chain = None
            self.pickchain(Chains.Nothing)
            return

        # We are on the stage
        else:
            edge_x = melee.stages.EDGE_GROUND_POSITION[gamestate.stage]
            edgedistance = abs(edge_x - abs(smashbro_state.position.x))

            randomgrab = False
            # if random.randint(0, 20) == 0:
            #     randomgrab = True
            # # Don't make this guaranteed, even on most aggressive mode. Make it common, but not predictable
            # if self.difficulty == 4 and random.randint(0, 10) == 0:
            #     randomgrab = True

            # For pikachu and jiggs don't grab the edge unless they're sitting, camping
            if opponent_state.character in [Character.PIKACHU, Character.JIGGLYPUFF] and opponent_state.action != Action.EDGE_HANGING:
                randomgrab = False

            # Can we challenge their ledge?
            framesleft = Punish.framesleft(opponent_state, self.framedata, smashbro_state)

            if opponent_state.action in [Action.EDGE_JUMP_1_QUICK, Action.EDGE_JUMP_2_QUICK, Action.EDGE_JUMP_1_SLOW, Action.EDGE_JUMP_2_SLOW]:
                if gamestate.distance < 15:
                    self.chain = None
                    tw_rng = random.randint(0, 1)
                    if tw_rng == 0:
                        # TODO fix
                        self.pickchain(Chains.AirAttack, [0, 0, 3, AIR_ATTACK_DIRECTION.FORWARD])
                        return
                    else:
                        # TODO fix
                        self.pickchain(Chains.AirAttack, [0, 0, 3, AIR_ATTACK_DIRECTION.NEUTRAL])
                        return

            # Grab edge out from under Pika quick-attack startup
            if opponent_state.character == Character.PIKACHU and opponent_state.action == Action.SWORD_DANCE_4_MID and opponent_state.action_frame < 7:
                self.pickchain(Chains.Grabedge, [True])
                return

            # Grab the edge when opponent starts a FireFox
            if opponent_state.character in [Character.FOX, Character.FALCO] and opponent_state.action == Action.SWORD_DANCE_3_LOW and (opponent_state.action_frame < 15):
                # But not if they're in range to grab the edge themselves
                edgedistance = abs(opponent_state.position.x) - (melee.stages.EDGE_GROUND_POSITION[gamestate.stage] + 15)
                in_immediate_range = (-5 > opponent_state.position.y > -28) and (edgedistance < 15)
                if not in_immediate_range:
                    self.pickchain(Chains.Grabedge, [True])
                    return

            # TODO add onstage edgeguards

            if opoutside and smashbro_state.position.y > -15: #and gamestate.stage != melee.enums.Stage.YOSHIS_STORY:
                if -15 < opponent_state.position.y < 10 and not opponent_state.on_ground and diff_x_opponent < 25\
                        and 10 < gamestate.distance < 20 and opponent_state.percent > 45 \
                        and not facinginwards and not (diff_x_opponent < 15 and opponent_state.position.y < 0):
                    self.chain = None
                    self.pickchain(Chains.Runofffair)
                    print('Edgeguard: opponent position', round(diff_x_opponent, 0), round(opponent_state.position.y, 0))
                    if smashbro_state.action_frame == 1:
                        print('edgeguard runoff fair')
                    return

            if opoutside and smashbro_state.on_ground:
                if diff_x_opponent < 20 and abs(opponent_state.position.y) < 20 and gamestate.distance < 10:
                    self.chain = None
                    self.pickchain(Chains.SmashAttack, [0, SMASH_DIRECTION.DOWN])
                    print('edgeguard dsmash')
                    return

            # waiting at edge
            if smashbro_state.on_ground and 20 < edgedistance < 25 and opponent_state.percent > 80:
                if diff_x_opponent < 30 and -30 < opponent_state.position.y < 0:
                    if smashbro_state.percent < 60:
                        self.chain = None
                        self.pickchain(Chains.Crouchcancel)
                        return

            if (not recoverhigh or randomgrab) and not onedge and opponent_state.invulnerability_left < 5 and \
                    edgedistance > 10 and smashbro_state.on_ground and opoutside:
                if (randomgrab or framesleft > 20) and opponent_state.action not in \
                        [Action.EDGE_ROLL_SLOW, Action.EDGE_ROLL_QUICK, Action.EDGE_GETUP_SLOW,
                         Action.EDGE_GETUP_QUICK, Action.EDGE_ATTACK_SLOW, Action.EDGE_ATTACK_QUICK]:  # if enough time left
                    if not self.framedata.is_attack(opponent_state.character, opponent_state.action):  # if no attack
                        ff_early = False
                        if opponent_state.character in [Character.FOX, Character.FALCO] and \
                                opponent_state.action == Action.SWORD_DANCE_3_LOW:
                            if opponent_state.action_frame < 20 and gamestate.distance > 60:
                                ff_early = True
                        if not ff_early:
                            self.pickchain(Chains.Grabedge, [True])
                            return

            # grab edge if far away enough
            if opponent_state.position.y < 30 < diff_x_opponent:
                self.pickchain(Chains.Grabedge, [True])
                return

            # Dash dance near the edge
            pivotpoint = opponent_state.position.x
            # Don't run off the stage though, adjust this back inwards a little if it's off
            edgebuffer = 5

            # make space for opponents near ledge
            if diff_x_opponent < 10:  # TODO adjust for better spacing
                edgebuffer = 20

            # Against Jigglypuff, we need to respect the ledge invulnerability. DD inwards more
            if opponent_state.character == Character.JIGGLYPUFF and opponent_state.invulnerability_left > 0:
                if self.logger:
                    self.logger.log("Notes", "staying safe: " + str(opponent_state.invulnerability_left) + " ",
                                    concat=True)
                if opponent_state.position.x > 0:
                    pivotpoint -= 10
                else:
                    pivotpoint += 10

            pivotpoint = min(pivotpoint, edge_x - edgebuffer)
            pivotpoint = max(pivotpoint, (-edge_x) + edgebuffer)

            self.chain = None
            self.pickchain(Chains.DashDance, [pivotpoint])

