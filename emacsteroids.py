#!/usr/bin/python

import os
import sys
import copy
import math
import curses
import random
import time

def clamp(num, minimum, maximum):
    return min(max(num,minimum),maximum)

class Vec:
    # XXX find a library?
    '''2D Vector.'''
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def magnitude(self):
        # XXX optimize?
        return int(math.sqrt(self.x*self.x+self.y*self.y))

class Box:
    '''position = top left of box'''
    def __init__(self, width, height, position=Vec(0,0)):
        self.position = position
        self.width = width
        self.height = height

    def top(self):
        return self.position.y

    def bottom(self):
        return self.position.y + self.height

    def left(self):
        return self.position.x

    def right(self):
        return self.position.x + self.width

    def contains_position(self, position):
        return (position.x >= self.left() and
                position.x <= self.right() and
                position.y >= self.top() and
                position.y <= self.bottom())

class CurStr:
    '''Curses text can have attributes'''
    def __init__(self, text, attr=curses.A_NORMAL):
        self.text = text
        self.attr = attr

# XXXJDR handle multi-line sprites
class Sprite:
    def __init__(self,
                 up=CurStr('@'),
                 down=CurStr('@'),
                 left=CurStr('@'),
                 right=CurStr('@'),
                 action=CurStr('@')):
        self.up = up
        self.down = down
        self.left = left
        self.right = right
        self.action = action
        self.size = Box(1,1)

class MovingThing(object):
    def __init__(self, position=Vec(0,0)):
        self.position = position
        self.direction = Vec(0,0)
        self.velocity = Vec(0,0)
        self.acceleration = Vec(0,0)
        self.deceleration = 1
        self.max_velocity = 1
        self.max_acceleration = 1
        self.sprite = None
        self.destructable = True
        self.movecounter = Vec(12,12)              # When the move counter == 0,
        self.maxmovecounter = 12                   # we actually do our move

    def update_position(self, boundary_box, moving_things):
        self.velocity.x = self.clamp_velocity(self.velocity.x + self.acceleration.x)
        self.velocity.y = self.clamp_velocity(self.velocity.y + self.acceleration.y)

        # Amount subtracted off should depend on current velocity...
        # XXX optimize?
        self.movecounter.x -= int(math.fabs(self.velocity.x))
        if self.movecounter.x <= 0:
            self.movecounter.x = self.maxmovecounter
            self.position.x += int(math.copysign(1, self.velocity.x))

        self.movecounter.y -= int(math.fabs(self.velocity.y))
        if self.movecounter.y <= 0:
            self.movecounter.y = self.maxmovecounter
            self.position.y += int(math.copysign(1, self.velocity.y))

        # Whoops, left the boundaries!
        if not boundary_box.contains_position(self.position):
            if self.destructable:
                moving_things.remove(self)
                return
            self.position.x = clamp(self.position.x,
                                    boundary_box.left(),
                                    boundary_box.right())
            self.position.y = clamp(self.position.y,
                                    boundary_box.top(),
                                    boundary_box.bottom())

    def clamp_velocity(self, velocity):
        return clamp(velocity, (-1)*self.max_velocity, self.max_velocity)

    def clamp_acceleration(self, acceleration):
        return clamp(acceleration, (-1)*self.max_acceleration, self.max_acceleration)

    def left(self):
        self.activesprite = self.sprite.left
        self.acceleration.x = self.clamp_acceleration(self.acceleration.x - 1)
        self.acceleration.y = 0
        self.direction.x = -1

    def right(self):
        self.activesprite = self.sprite.right
        self.acceleration.x = self.clamp_acceleration(self.acceleration.x + 1)
        self.acceleration.y = 0
        self.direction.x = 1

    def down(self):
        self.activesprite = self.sprite.down
        self.acceleration.y = self.clamp_acceleration(self.acceleration.y + 1)
        self.acceleration.x = 0
        self.direction.y = 1

    def up(self):
        self.activesprite = self.sprite.up
        self.acceleration.y = self.clamp_acceleration(self.acceleration.y - 1)
        self.acceleration.x = 0
        self.direction.y = -1

    def draw(self, screen, viewbox):
        if viewbox.contains_position(self.position):
            screen.addch(self.position.y,
                         self.position.x,
                         self.activesprite.text,
                         self.activesprite.attr)

    def collide(self):
        self.direction.x = self.velocity.x
        self.direction.y = self.velocity.y
        self.acceleration = Vec(0,0)
        self.velocity = Vec(0,0)
        return True

    def destroy(self, moving_things):
        moving_things.remove(self)
        return 0

class Ship(MovingThing):
    def __init__(self):
        super(Ship, self).__init__()
        self.sprite = Sprite(up=CurStr('^'),
                             down=CurStr('v'),
                             left=CurStr('<'),
                             right=CurStr('>'))
        self.activesprite = self.sprite.up
        self.keymap = { ord('a') : self.left,
                        ord('d') : self.right,
                        ord('s') : self.down,
                        ord('w') : self.up,
                        }
#        self.max_velocity = 3
        self.destructable = False
        self.max_velocity = 1
        self.max_acceleration = 1


    def resolve_input(self, key):
        if key not in self.keymap.keys():
            return
        self.keymap[key]()

    def destroy(self, moving_things):
        return -5

    def pewpew(self, moving_things):
        pos = copy.deepcopy(self.position)
        pos.x += self.velocity.x
        pos.y += self.velocity.y

        vel = copy.deepcopy(self.velocity)
        acc = copy.deepcopy(self.acceleration)

        acc.x += self.direction.x
        acc.y += self.direction.y

        moving_things.append(PewPew(pos,vel,acc))

    def boom(self, moving_things):
        pos = copy.deepcopy(self.position)
        pos.x += self.velocity.x
        pos.y += self.velocity.y

        vel = copy.deepcopy(self.velocity)
        acc = copy.deepcopy(self.acceleration)

        acc.x += self.direction.x
        acc.y += self.direction.y

        moving_things.append(Boom(pos,vel,acc))


class PewPew(MovingThing):
    def __init__(self, position, velocity, acceleration):
        super(PewPew, self).__init__()
        self.acceleration = acceleration
        self.velocity = velocity
        self.position = position
        self.max_acceleration = 2
        self.max_velocity = 5
        self.activesprite = CurStr('*')

    def destroy(self, moving_things):
        moving_things.remove(self)
        return random.random()*100

class Boom(MovingThing):
    def __init__(self, position, velocity, acceleration):
        super(Boom, self).__init__()
        self.acceleration = acceleration
        self.velocity = velocity
        self.position = position
        self.max_acceleration = 2
        self.max_velocity = 5
        self.activesprite = CurStr('o')

    def destroy(self, moving_things):
        # XXX bounds checking
        pos = copy.deepcopy(self.position)
        pos.x += 1
        vel = Vec(1,0)
        acc = Vec(1,0)
        moving_things.append(PewPew(pos,vel,acc))

        pos = copy.deepcopy(self.position)
        pos.x -= 1
        vel = Vec(-1,0)
        acc = Vec(-1,0)
        moving_things.append(PewPew(pos,vel,acc))

        pos = copy.deepcopy(self.position)
        pos.y += 1
        vel = Vec(0,1)
        acc = Vec(0,1)
        moving_things.append(PewPew(pos,vel,acc))

        pos1 = copy.deepcopy(self.position)
        pos1.y -= 1
        vel = Vec(0,-1)
        acc = Vec(0,-1)
        moving_things.append(PewPew(pos,vel,acc))

        moving_things.remove(self)
        return random.random()*100
    
class Level:
    def __init__(self, filename, min_width=0, min_height=0):
        f = open(filename, 'r')
        self.name = filename
        self.width = min_width
        self.height = 1
        for line in f:
            self.width = max(len(line), self.width)
            self.height+=1
        self.height = max(min_height, self.height)

        self.map = curses.newpad(self.height+1, self.width+1)
        self.objectpad = curses.newpad(self.height+1, self.width+1)
        self.boundaries = Box(self.width, self.height-2)

        # Read the text of the file into the level
        f.seek(0)
        lineno = 0
        for line in f:
            self.map.addstr(lineno,0,line.rstrip('\n'))
            lineno += 1

class Engine:
    def __init__(self):
        self.player = Ship()
        self.moving_things = [self.player]
        self.points = 0

        self.level = None

        self.display = CursesDisplay()

    def load_level(self, filename):
        self.level = Level(filename,
                           self.display.viewbox.width,
                           self.display.viewbox.height)
        self.display.set_level(self.level)

    def resolve_movement(self, moving_things, level):
        newpoints = 0
    
        for moving_thing in self.moving_things:
            moving_thing.update_position(self.level.boundaries, moving_things)

        for moving_thing in self.moving_things:
            if (self.level.map.inch(moving_thing.position.y, moving_thing.position.x) != ord(' ')
                and moving_thing.collide()):
                self.level.map.addstr(moving_thing.position.y,
                                      moving_thing.position.x,
                                      ' ')
                newpoints += moving_thing.destroy(self.moving_things)

        return newpoints

    def run(self):
        '''Main game loop. Each iteration should take at least TICK time'''
        while True:
            if not self.display.process_input(self.player, self.moving_things):
                break
            self.points += self.resolve_movement(self.moving_things, self.level)
            self.display.draw_screen(self.player, self.level, self.moving_things, self.points)

    def shutdown(self):
        # XXX there's got to be a nicer way to do this
        self.display.curses_deinit()

class CursesDisplay:
    def __init__(self):
        self.screen = None
        self.oldvis = 0

        self.curses_init()
        
        self.levelsize = Box(0,0)
        self.levelname = "No level"

        maxy, maxx = self.screen.getmaxyx()
        maxy -= 1
        maxx -= 1

        self.viewbox = Box(width=maxx,
                           height=maxy-1,
                           position=Vec(0,0))

        self.scrollbox = Box(width=int(self.viewbox.width/3),
                             height=int(self.viewbox.height/3),
                             position=Vec(int(self.viewbox.width/3),
                                          int(self.viewbox.height/3)))

    def set_level(self, level):
        self.levelsize = level.boundaries
        self.levelname = level.name

    def rejigger_view(self, position):
        # Adjust the view so the point of interest is inside the scrollbox
        if position.y < (self.viewbox.top() + self.scrollbox.top()):
            self.viewbox.position.y = position.y - self.scrollbox.top()
        elif position.y > (self.viewbox.top() + self.scrollbox.bottom()):
            self.viewbox.position.y = position.y - self.scrollbox.bottom()
        if position.x < (self.viewbox.left() + self.scrollbox.left()):
            self.viewbox.position.x = position.x - self.scrollbox.left()
        elif position.x > (self.viewbox.left() + self.scrollbox.right()):
            self.viewbox.position.x = position.x - self.scrollbox.right()

        self.viewbox.position.y = clamp(self.viewbox.position.y,
                                        0,
                                        self.levelsize.height - self.viewbox.height)
        self.viewbox.position.x = clamp(self.viewbox.position.x,
                                        0,
                                        self.levelsize.width - self.viewbox.width)

    def add_status(self, points, player):
        if points == 0:
            msg1 = '-UU-:----F1  '
        else:
            msg1 = '-UU-:**--F1  '
        msg2 = ' Points: %d   (%d,%d)   (Pewpew)' % (points, player.position.x, player.position.y)

        self.screen.addstr(self.viewbox.height, 0, msg1, curses.A_REVERSE)
        self.screen.addstr(self.levelname, curses.A_BOLD | curses.A_REVERSE)
        self.screen.addstr(msg2, curses.A_REVERSE)
        remaining_width = self.viewbox.width-len(msg1)-len(self.levelname)-len(msg2)
        self.screen.addstr('-'*remaining_width, curses.A_REVERSE)

    def process_input(self, player, moving_things):
        c = self.screen.getch()
        if c == ord('x'):
            return False
        elif c in player.keymap.keys():
            player.resolve_input(c)
        elif c == ord(' '):
            player.pewpew(moving_things)
        elif c == ord('l'):
            player.boom(moving_things)

        return True

    def draw_screen(self, player, level, moving_things, points):
        self.rejigger_view(player.position)

        level.objectpad.erase()
        self.screen.erase()

        for moving_thing in moving_things:
            moving_thing.draw(level.objectpad, self.viewbox)

        level.map.overlay(self.screen, self.viewbox.top(), self.viewbox.left(), 0, 0,
                          self.viewbox.height-1, self.viewbox.width)
        level.objectpad.overlay(self.screen, self.viewbox.top(), self.viewbox.left(), 0, 0,
                                self.viewbox.height-1, self.viewbox.width)
        self.add_status(points, player)

        curses.doupdate()

    def curses_init(self):
        self.screen = curses.initscr()
        self.screen.keypad(1)
        self.screen.timeout(8)
        curses.noecho()
        curses.cbreak()
        self.oldvis = curses.curs_set(0)

    def curses_deinit(self):
        self.screen.keypad(0)
        curses.curs_set(self.oldvis)
        curses.nocbreak()
        curses.echo()
        curses.endwin()

def main(argv):
    if len(argv) != 2:
        print "Usage: %s filename" % argv[0]
        return

    engine = Engine()
    engine.load_level(argv[1])
    engine.run()
    engine.shutdown()

    # Stopgap until I can get curses deinit to behave
    os.popen('reset')

if __name__ == "__main__":
    main(sys.argv)
        
