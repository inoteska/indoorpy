#!/bin/python

# ###############################################################
#
# Imports
#
# ###############################################################

import kivy
kivy.require('1.9.0')

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.config import ConfigParser
from kivy.core.window import Window
#from kivy.graphics import Color, Rectangle
from kivy.graphics import Color, Line, Rectangle, Ellipse
from kivy.lang import Builder
from kivy.network.urlrequest import UrlRequest
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scatter import Scatter
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.vkeyboard import VKeyboard
from kivy.uix.widget import Widget

from math import cos, sin, pi

import atexit
import datetime

import os
import signal
import socket
import subprocess
import sys
import time

import pjsua as pj

#import my_lib as m_ss


#Builder.load_file('main1.kv')


###############################################################
#
# Declarations
#
# ###############################################################

CMD_KILL = 'kill -9 '

CONFIG_FILE = 'indoorconfig.ini'

APP_NAME = '-Indoor-2.0-'

SCREEN_SAVER = 0

BUTTON_CALL_ANSWER = '=Answer Call='
BUTTON_CALL_HANGUP = '=HangUp Call='
BUTTON_DO_CALL = '=Do Call='

BUTTON_DOOR_1 = '=Open Door 1='
BUTTON_DOOR_2 = '=Open Door 2='

WAIT_SCR = 'waitscr'
WATCH_SCR = 'clock'
CAMERA_SCR = 'camera'
SETTINGS_SCR = 'settings'

COLOR_BUTTON_BASIC = 1,1,1,1
COLOR_ANSWER_CALL = 1,0,0,1
COLOR_HANGUP_CALL = 1,1,0,1
COLOR_NOMORE_CALL = COLOR_BUTTON_BASIC

ACTIVE_DISPLAY_BACKGROUND = Color(1.,1.,.0)
INACTIVE_DISPLAY_BACKGROUND = Color(.5,.0,.0)

LOG_LEVEL = 3
current_call = None
acc = None

main_state = 0
docall_button_global = None

active_display_index = 0

ring_event = None
APLAYER = 'aplay'
APARAMS = '-q -N -f cd -D plughw:1,0'
RING_WAV = APLAYER + ' ' + APARAMS + ' ' +'share/sounds/linphone/rings/oldphone.wav &'

TRANSPARENCY_VIDEO_CMD = ['setalpha']

DBUS_PLAYERNAME = 'org.mpris.MediaPlayer2.omxplayer'

transparency_value = 0
transparency_event = None

mainLayout = None

procs = []


# ###############################################################
#
# Functions
#
# ###############################################################

@atexit.register
def kill_subprocesses():
    "tidy up at exit or break"
    print('destroy lib at exit')
    try:
	pj.Lib.destroy()
    except:
	pass
    print('kill subprocesses at exit')
    for proc in procs:
	try:
            proc.kill()
	except:
	    pass


# ##############################################################################

def playWAV(dt):
    "start play"
    global RING_WAV
    try:
        os.system(RING_WAV)
    except:
	pass


# ##############################################################################

def stopWAV():
    "stop play"
    global ring_event
    Clock.unschedule(ring_event)
    ring_event = None
    os.system('pkill -9 ' + APLAYER)


# ##############################################################################

def send_dbus(dst,args):
    "send DBUS command to omxplayer"
#    cmd = ' '.join(map(str, ['./dbuscntrl.sh', dst] + args))
    try:
#        os.system(cmd)
	proc = subprocess.Popen(['./dbuscntrl.sh', dst] + args)
	try:
	    outs, errs = proc.communicate(timeout=2)
	except TimeoutExpired:
	    proc.kill()
    except:
	pass

#    print 'sendDBUS...', cmd


# ###############################################################
#
# Classes
#
# ###############################################################

class DigiClockWidget(FloatLayout):
    "Clock class - digital"
    pass


# ##############################################################################

class DigiClock(Label):
    "Label with date & time"
    def __init__(self, **kwargs):
        super(DigiClock, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 1)

    def update(self, *args):
        self.text = datetime.datetime.now().strftime("%d.%m.%Y     %H:%M:%S")


# ##############################################################################

class MyClockWidget(FloatLayout):
    "Clock class - analog"
    pass


# ##############################################################################

class Ticks(Widget):
    "Analog watches"
    galleryIndex = 0
    gallery = []
    ln = Label()

    def __init__(self, **kwargs):
        super(Ticks, self).__init__(**kwargs)
        self.bind(pos = self.update_clock)
        self.bind(size = self.update_clock)

        self.ln.text = '[color=ff3333] ' + APP_NAME + ' [/color]'
        self.ln.pos = self.pos
        self.ln.size = self.size
        self.ln.font_size = '32sp'
        self.ln.text_size = self.size
        self.ln.halign = 'right'
        self.ln.valign = 'bottom'
        self.ln.markup = True

        Clock.schedule_interval(self.update_clock, 1)


    def update_clock(self, *args):
        time = datetime.datetime.now()
        self.canvas.clear()

        self.remove_widget(self.ln)
        self.ln.pos = self.pos
        self.ln.size = self.size
        self.ln.text = '[color=ff3333] ' + APP_NAME + ' [/color]'
        self.ln.text_size = self.size
        self.add_widget(self.ln)

        with self.canvas:
            Color(.1, .1, .6, .15)
            Ellipse(pos={self.y + 19,self.width / 4}, size={self.width / 2, self.height - 38})

            Color(0.6, 0.6, 0.9)
            Line(points = [self.center_x, self.center_y, self.center_x+0.7*self.r*sin(pi/30*time.second),
                self.center_y+0.7*self.r*cos(pi/30*time.second)], width=1, cap="round")
            Color(0.5, 0.5, 0.8)
            Line(points = [self.center_x, self.center_y, self.center_x+0.6*self.r*sin(pi/30*time.minute),
                self.center_y+0.6*self.r*cos(pi/30*time.minute)], width=2, cap="round")
            Color(0.4, 0.4, 0.7)
            th = time.hour*60 + time.minute
            Line(points = [self.center_x, self.center_y, self.center_x+0.5*self.r*sin(pi/360*th),
            self.center_y+0.5*self.r*cos(pi/360*th)], width=3, cap="round")


# ##############################################################################

class MyAccountCallback(pj.AccountCallback):
    "Callback to receive events from account"
    def __init__(self, account=None):
        pj.AccountCallback.__init__(self, account)

    # Notification on incoming call
    def on_incoming_call(self, call):
        global current_call, mainLayout
        if current_call:
            call.answer(486, "Busy")
            return

        print "Incoming call from ", call.info().remote_uri
	mainLayout.findTargetWindow(call.info().remote_uri)

        current_call = call

        call_cb = MyCallCallback(current_call)
        current_call.set_callback(call_cb)

        current_call.answer(180)


def log_cb(level, str, len):
    "pjSip logging callback"
    print str,


class MyCallCallback(pj.CallCallback):
    "Callback to receive events from Call"
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)

    def on_state(self):
	"Notification when call state has changed"
        global current_call, ring_event, transparency_value
        global main_state, mainLayout, docall_button_global
        print "Call with", self.call.info().remote_uri,
        print "is", self.call.info().state_text, self.call.info().state,
        print "last code =", self.call.info().last_code,
        print "(" + self.call.info().last_reason + ")"

        main_state = self.call.info().state
        transparency_value = 0

        if main_state == pj.CallState.DISCONNECTED:
            current_call = None
	    mainLayout.setButtons(False)
#            print 'Current call is', current_call

        if main_state == pj.CallState.EARLY:
            ring_event = Clock.schedule_interval(playWAV, 3.5)
            playWAV(3.5)
        else:
            stopWAV()

        if main_state == pj.CallState.INCOMING:
		mainLayout.findTargetWindow(self.call.info().remote_uri)

        if main_state == pj.CallState.INCOMING or\
           main_state == pj.CallState.EARLY:
            if main_state is not pj.CallState.CALLING:
		docall_button_global.color = COLOR_ANSWER_CALL
		docall_button_global.text = BUTTON_CALL_ANSWER
#		mainLayout.findTargetWindow(self.call.info().remote_uri)

        if main_state == pj.CallState.DISCONNECTED:
            docall_button_global.color = COLOR_NOMORE_CALL
            docall_button_global.text = BUTTON_DO_CALL
	    mainLayout.startScreenTiming()

        if main_state == pj.CallState.CONFIRMED:
            docall_button_global.color = COLOR_HANGUP_CALL
            docall_button_global.text = BUTTON_CALL_HANGUP

        if main_state == pj.CallState.CALLING:
	    current_call = self.call
            docall_button_global.color = COLOR_HANGUP_CALL
            docall_button_global.text = BUTTON_CALL_HANGUP
	    mainLayout.findTargetWindow('') #self.call.info().remote_uri)


    def on_media_state(self):
	"Notification when call's media state has changed"
        if self.call.info().media_state == pj.MediaState.ACTIVE:
            # Connect the call to sound device
            call_slot = self.call.info().conf_slot
            pj.Lib.instance().conf_connect(call_slot, 0)
            pj.Lib.instance().conf_connect(0, call_slot)
#            print "Media is now active"
#        else:
#            print "Media is inactive"


def make_call(uri):
    "Function to make outgoing call"
    global acc
    try:
        print "Making call to", uri, acc
	if acc != None:
	    return acc.make_call(uri, cb=MyCallCallback(pj.CallCallback))
	else:
	    return None
    except pj.Error, e:
        print "Exception: " + str(e)
        return None


# ##############################################################################

class BasicDisplay:
    "basic screen class"
    def __init__(self,winpos,servaddr,streamaddr):
	"display area init"
	self.screenIndex = len(procs)
	self.winPosition = winpos.split(',')
	self.winPosition = [int(i) for i in self.winPosition]
	self.serverAddr = str(servaddr)
	self.streamUrl = str(streamaddr)
	self.playerPosition = [i for i in self.winPosition]

	delta = 1
	self.playerPosition[0] += delta
	self.playerPosition[1] += delta
	self.playerPosition[2] -= delta
	self.playerPosition[3] -= delta
	self.playerPosition = [str(i) for i in self.playerPosition]

	procs.append(self.initPlayer())

	self.color = None
	self.frame = None

	self.printInfo()
	self.setActive(False)


    def testTouchArea(self, x, y):
	"test if touch is in display area"
	y = 480 - y                        # touch position is from bottom to up
	retx = False
	rety = False
	if self.winPosition[0] < x and self.winPosition[2] > x : retx = True
	if self.winPosition[1] < y and self.winPosition[3] > y : rety = True
	return retx and rety


    def initPlayer(self):
	"start video player"
	return subprocess.Popen(['omxplayer', '--live', '--no-osd',\
	    '--dbus_name',DBUS_PLAYERNAME + str(self.screenIndex),\
	    '--layer', '1', '--no-keys', '--win', ','.join(self.playerPosition), self.streamUrl],\
	    stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE) #, close_fds = True)


    def hidePlayer(self):
	"hide video player area"
	if self.color is not None: mainLayout.canvas.remove(self.color)
	if self.frame is not None: mainLayout.canvas.remove(self.frame)


    def setActive(self, active=True):
	"add or remove active flag"
	self.hidePlayer()

	if active:
	    self.color = ACTIVE_DISPLAY_BACKGROUND
	else:
	    self.color = INACTIVE_DISPLAY_BACKGROUND

	w = self.winPosition[2] - self.winPosition[0] # width
	h = self.winPosition[3] - self.winPosition[1] # height
	ltx = self.winPosition[0]
	lty = 480 - self.winPosition[1] - h           # touch position is from bottom to up

	self.frame = Rectangle(pos=(ltx, lty), size=(w, h))
	mainLayout.canvas.add(self.color)
	mainLayout.canvas.add(self.frame)


    def printInfo(self):
	"print class info"
	print self.screenIndex,'area:',self.winPosition, 'IPaddr:', self.serverAddr, 'stream:', self.streamUrl


# ##############################################################################

class Indoor(FloatLayout):
    def __init__(self, **kwargs):
	"app init"
        global BUTTON_DO_CALL, BUTTON_CALL_ANSWER, BUTTON_CALL_HANGUP
        global BUTTON_DOOR_1, BUTTON_DOOR_2, APP_NAME, SCREEN_SAVER
        global main_state, docall_button_global, mainLayout

        super(Indoor, self).__init__(**kwargs)

	mainLayout = self

	self.displays = []

        main_state = 0
        self.info_state = 0
        self.myprocess = None

	self.scrmngr = self.ids._screen_manager

        # nacitanie konfiguracie
        config = ConfigParser()
        try:
            config.read('./' + CONFIG_FILE)
        except:
            self.dbg('ERROR 1: read config file!')

            try:
                config.read(dirname(__file__) + '/' + CONFIG_FILE)
            except:
                self.dbg('ERROR 2: read config file!')

        try:
	    APP_NAME = config.get('command', 'app_name')
	    screen_saver = int(config.get('command', 'screen_saver'))
	    if screen_saver > 0 and screen_saver < 120: SCREEN_SAVER = screen_saver * 60
        except:
            self.dbg('ERROR 3: read config file!')

        try:
            BUTTON_DO_CALL = config.get('gui', 'btn_docall')
            BUTTON_CALL_ANSWER = config.get('gui', 'btn_call_answer')
            BUTTON_CALL_HANGUP = config.get('gui', 'btn_call_hangup')
            BUTTON_DOOR_1 = config.get('gui', 'btn_door_1')
            BUTTON_DOOR_2 = config.get('gui', 'btn_door_2')
        except:
            self.dbg('ERROR: read config file!')

        self.infinite_event = Clock.schedule_interval(self.infinite_loop, 6.9)
        Clock.schedule_interval(self.info_state_loop, 10.)

        self.init_myphone()

	self.init_screen(config)

        self.ids.btnDoor1.text = BUTTON_DOOR_1
        self.ids.btnDoor1.color = COLOR_BUTTON_BASIC
        self.ids.btnDoor2.text = BUTTON_DOOR_2
        self.ids.btnDoor2.color = COLOR_BUTTON_BASIC
        docall_button_global = self.ids.btnDoCall
        docall_button_global.text = BUTTON_DO_CALL
        docall_button_global.color = COLOR_BUTTON_BASIC


    def init_screen(self, cfg):
	"define app screen"
	scr_mode = cfg.get('gui', 'screen_mode')
	if scr_mode == None or scr_mode == '': scr_mode = 0

	self.scrmngr.current = WAIT_SCR

	if scr_mode == 1:
	    wins = ['0,0,800,432']
	elif scr_mode == 2:
	    wins = ['0,0,800,216', '0,216,800,432']
	elif scr_mode == 3:
	    wins = ['0,0,400,432', '400,0,800,432']
	else:
	    wins = ['0,0,400,216', '400,0,800,216', '0,216,400,432', '400,216,800,432']

	self.dbg('scr_mode:' + str( scr_mode ) + ' wrange:' + str(len(wins)))

	for i in range(0,len(wins)):
	    win = wins[i]
	    serv = cfg.get('common', 'server_ip_address_'+str(i + 1))
	    vid = cfg.get('common', 'server_stream_'+str(i + 1))

	    displ = BasicDisplay(win,serv,vid)
	    self.displays.append(displ)

	if scr_mode != 1: self.displays[0].setActive()

	self.scrmngr.current = CAMERA_SCR
	self.setButtons(False)


    def init_myphone(self):
	"sip phone init"
        global acc

        # Create library instance
        lib = pj.Lib()

        try:
            # Init library with default config and some customized logging config
            lib.init(log_cfg = pj.LogConfig(level=LOG_LEVEL, callback=log_cb))

	    comSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    comSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Create UDP transport which listens to any available port
            transport = lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(5060))

            print "\nListening on", transport.info().host, "port", transport.info().port, "\n"

            # Start the library
            lib.start()

            # Create local account
            acc = lib.create_account_for_transport(transport, cb=MyAccountCallback())

            my_sip_uri = "sip:" + transport.info().host + ":" + str(transport.info().port)
            print "\nAccount", acc, "at URI", my_sip_uri, "\n"

        except pj.Error, e:
            print "Exception: " + str(e)
            lib.destroy()
            lib = None


    def info_state_loop(self, dt):
	"state loop"
        global current_call, docall_button_global, BUTTON_DO_CALL
#
        if current_call is not None: self.info_state = 0
#
        if self.info_state == 0:
            self.info_state = 1
#            self.ids.btnDoor1.text = BUTTON_DOOR_1
#            self.ids.btnDoor2.text = BUTTON_DOOR_2
        elif self.info_state == 1:
            self.info_state = 2
#            self.ids.btnDoor2.text = datetime.datetime.now().strftime("%H:%M")
        elif self.info_state == 2:
            self.info_state = 3
#            self.ids.btnDoor1.text = BUTTON_DOOR_1 #'(c) Inoteska'
#            self.ids.btnDoor2.text = BUTTON_DOOR_2
            if current_call is None: docall_button_global.text = BUTTON_DO_CALL
        elif self.info_state == 3:
            self.info_state = 0
#            self.ids.btnDoor1.text = datetime.datetime.now().strftime("%d.%m.%Y")


    def infinite_loop(self, dt):
	"main neverendig loop"
        global current_call, main_state

	if len(procs) == 0: return

	for idx, p in enumerate(procs):
	    if p.poll() is not None:
		self.dbg( "Process" + str(idx) + " (" + str(p.pid) + ") is dead")
		try:
		    p.kill()
		    os.system(CMD_KILL + str(p.pid))
		except:
		    pass
		procs[idx] = self.displays[idx].initPlayer()


    def startScreenTiming(self):
	"start screen timer"
#        self.dbg('ScrnEnter:'+str(SCREEN_SAVER))
        if SCREEN_SAVER > 0: Clock.schedule_once(self.return2clock, SCREEN_SAVER)


    def return2clock(self, *args):
	"swat screen to CLOCK"
	global current_call

#        self.dbg('2 clock')
	if current_call is None:
            self.scrmngr.current = WATCH_SCR


    def finishScreenTiming(self):
	"finist screen timer"
#        self.dbg('ScrnLeave')
        Clock.unschedule(self.return2clock)


    def callback_btn_docall(self):
	"make outgoing call"
        global current_call, active_display_index, docall_button_global, BUTTON_DO_CALL

	if len(procs) == 0: return

	target = self.displays[active_display_index].serverAddr
#        self.dbg(BUTTON_DO_CALL + ' --> ' + 'sip:' + target + ':5060')

        self.rstTransparency()

        if current_call is not None:
#	    txt = BUTTON_DO_CALL
            if main_state == pj.CallState.EARLY:
                stopWAV()
                current_call.answer(200)
		self.setButtons(True)
            else:
                current_call.hangup()
		self.setButtons(False)
	else:
	    txt = '--> ' + str(active_display_index + 1)
	    if make_call('sip:' + target + ':5060') is None: txt = txt + ' ERROR'

	    docall_button_global.text = txt
	    self.setButtons(True)


    def gotResponse(self, req, results):
	"relay result"
#        print 'Relay: ', req, results
        pass


    def setRelayRQ(self, relay):
	"send relay request"
        global active_display_index

	if len(procs) == 0: return

	target = self.displays[active_display_index].serverAddr

        req = UrlRequest('http://' + target + '/cgi-bin/remctrl.sh?id=' + relay,\
                on_success = self.gotResponse, timeout = 5)


    def callback_btn_door1(self):
	"door 1 button"
        self.dbg(BUTTON_DOOR_1)
        self.setRelayRQ('relay1')
        self.rstTransparency()


    def callback_btn_door2(self):
	"door 2 button"
        self.dbg(BUTTON_DOOR_2)
        self.setRelayRQ('relay2')
        self.rstTransparency()


    def settings_callback(self):
	"callback after closing settings dialog"
#        global transparency_event, transparency_value

#        transparency_value = 16
##        self.rstTransparency(200)
#        if transparency_event is None:
#            transparency_event = Clock.schedule_interval(self.transparency_loop, .05)

        self.dbg('Save Settings!')

	try:
	    os.system('pkill omxplayer')
	    os.system('pkill dbus-daemon')
	    os.system('pkill python')
	except:
	    pass
	App.get_running_app().stop()


    def callback_set_options(self):
	"start settings"
	global procs
        self.dbg(self.ids.btnSetOptions.text)

	if len(procs) == 0: return

	self.hidePlayers()

	for idx, p in enumerate(procs):
	    if p.poll() is not None:
		self.dbg( "Process" + str(idx) + " (" + str(p.pid) + ") is dead")
		try:
		    p.kill()
		    os.system(CMD_KILL + str(p.pid))
		except:
		    pass
	procs = []
	self.displays = []

	try:
	    os.system('pkill omxplayer')
	    os.system('pkill dbus-daemon')
	except:
	    pass

	self.finishScreenTiming()
        self.scrmngr.current = SETTINGS_SCR

	gl = GridLayout(cols=2, row_force_default=True, row_default_height=80)

	self._keyboard = VKeyboard(layout='azerty')
	self._keyboard.bind(on_key_down=self._on_keyboard_down)
        gl.add_widget(Label(text='IP address'))
        self.ipaddress = TextInput(multiline=False, focus=True)
	self.ipaddress.text = ''
        gl.add_widget(self.ipaddress)
	self.add_widget(gl)
        self.add_widget(self._keyboard)

        print 'keyboard?', self._keyboard


    def callback_set_voice(self, value):
	"volume buttons"
	if self.ids.btnScreenClock.text == 'C':
	    if value == -1:
		self.callback_set_options()
	    else:
#		self.finishScreenTiming()
		Clock.schedule_once(self.return2clock, .2)
	else :
            self.dbg('Voice: ' + str(value))


    def on_touch_up(self, touch):
	"process touch up event"
	global active_display_index
#        print 'touchUp: ', touch.x, touch.y, touch.is_double_tap

	if len(procs) == 0: return

	if touch.is_double_tap:
#	    self.finishScreenTiming()
	    self.callback_set_options()
	    return

	self.startScreenTiming()

	rx = int(round(touch.x))
	ry = int(round(touch.y))

	for idx, d in enumerate(self.displays):
	    t = d.testTouchArea(rx, ry)
	    if t:
		active_display_index = idx
	    else:
		d.setActive(False)

	self.displays[active_display_index].setActive()


    def _keyboard_closed(self):
	print 'keyboard closed'
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

	self.settings_callback()


    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
	print 'kbd_down', keyboard, keycode, text, modifiers

	if str(keycode) == str('escape') or keycode == 'layout':
	    self._keyboard_closed()
	    print 'ESC'
	    return False
	elif str(keycode) == str('backspace'):
	    print 'BSP'
	    self.ipaddress.text = self.ipaddress.text[:-1]
	    return False

	if str(text) in ['0','1','2','3','4','5','6','7','8','9','.']:
	    self.ipaddress.text += str(text)
        return True


#    def main_touch(self):
#	"touch on the screen"
#        global transparency_event, transparency_value, current_call
#
#        Clock.unschedule(self.infinite_event)
#        self.infinite_event = Clock.schedule_interval(self.infinite_loop, 6.9)
#
#        if current_call is not None:
#            self.rstTransparency()
#            return
#
##        transparency_value = 200
#        self.rstTransparency(200)
#        if transparency_event is None:
#            transparency_event = Clock.schedule_interval(self.transparency_loop, .05)
#
#
    def showPlayers(self):
	"d-bus command to show video"
        self.dbg('show players')
        for idx, proc in enumerate(procs):
            send_dbus(DBUS_PLAYERNAME + str(idx), TRANSPARENCY_VIDEO_CMD + [str(255)])

	self.displays[active_display_index].setActive()


    def hidePlayers(self):
	"d-bus command to hide video"
        self.dbg('hide players')
        for idx, proc in enumerate(procs):
	    self.displays[idx].hidePlayer()
            send_dbus(DBUS_PLAYERNAME + str(idx), TRANSPARENCY_VIDEO_CMD + [str(0)])

    def setButtons(self, visible):
	"set buttons (ScrSaver, Options, Voice+-) to accurate state"

	if visible:
#	    self.ids.btnScreenClock.size_hint_x = .01
#	    self.ids.btnSetOptions.size_hint_x = .01
#	    self.ids.btnVoicePlus.size_hint_x = .3
#	    self.ids.btnVoiceMinus.size_hint_x = .3
	    self.ids.btnScreenClock.text = '+'
	    self.ids.btnSetOptions.text = '-'
	else:
#	    self.ids.btnScreenClock.size_hint_x = .3
#	    self.ids.btnSetOptions.size_hint_x = .3
#	    self.ids.btnVoicePlus.size_hint_x = .01
#	    self.ids.btnVoiceMinus.size_hint_x = .01
	    self.ids.btnScreenClock.text = 'C'
	    self.ids.btnSetOptions.text = 'S'


    def findTargetWindow(self, addr):
	"find target window according to calling address"
	global active_display_index
        self.dbg('find target window for:' + addr)

	self.scrmngr.current = CAMERA_SCR
	self.finishScreenTiming()

	if addr != '':
	    active_display_index = 0
	    for idx, d in enumerate(self.displays):
		d.setActive(False)
		if d.serverAddr in addr:
		    active_display_index = idx

	    self.dbg('target window:' + str(active_display_index))
	    self.displays[active_display_index].setActive()


    def transparency_loop(self, dt):
	"unhide loop"
#        self.dbg('transparency ' + str(transparency_value))
        global transparency_value, transparency_event

#        if transparency_event is None: return

        if transparency_value > 0 and transparency_value < 250:
            transparency_value -= 8

        for idx, proc in enumerate(procs):
            send_dbus(DBUS_PLAYERNAME + str(idx), TRANSPARENCY_VIDEO_CMD + [str(255 - transparency_value)])

        if transparency_value <= 0 and transparency_event is not None:
            Clock.unschedule(transparency_event)
            transparency_event = None
	    transparency_value = 0


    def rstTransparency(self, val = 0):
	"set transparency"
#        global transparency_value
	self.dbg('rstTransparency')
	return

        transparency_value = val
        self.transparency_loop(0)


    def dbg(self, info):
	"debug outputs"
        print info


# ###############################################################

class IndoorApp(App):
    def build(self):
        self.dbg('Hello Indoor 2.0')
#        Config.set('kivy', 'keyboard_mode','')
	lbl = 'Configuration keyboard_mode is %r, keyboard_layout is %r' % (
	    Config.get('kivy', 'keyboard_mode'),
	    Config.get('kivy', 'keyboard_layout'))
        self.dbg(lbl)
        return Indoor()

    def on_start(self):
        self.dbg('START')

    def on_stop(self):
        self.dbg('STOP')
#        lib.destroy()

    def dbg(self, info):
        print info


# ###############################################################
#
# Start
#
# ###############################################################

if __name__ == '__main__':
    IndoorApp().run()
