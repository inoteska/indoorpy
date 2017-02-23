#!/bin/python

# ###############################################################
#
# Imports
#
# ###############################################################

import kivy
kivy.require('1.9.0')


from kivy.app import App
from kivy.adapters.listadapter import ListAdapter
from kivy.clock import Clock
from kivy.config import Config, ConfigParser
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger, LoggerHistory
from kivy.network.urlrequest import UrlRequest
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.listview import ListView, ListItemLabel
from kivy.uix.popup import Popup
from kivy.uix.settings import Settings, SettingsWithSidebar
from kivy.uix.scatter import Scatter
from kivy.uix.screenmanager import ScreenManager, Screen
#from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import atexit
import datetime
from datetime import timedelta
import json

import signal
import socket
import subprocess
from threading import Thread
import time

import pjsua as pj

from my_lib import *


###############################################################
#
# Declarations
#
# ###############################################################

config = get_config()


# ###############################################################
#
# Functions
#
# ###############################################################

@atexit.register
def kill_subprocesses():
    "tidy up at exit or break"

    Logger.info(whoami() +': destroy lib at exit')
    try:
	pj.Lib.destroy()
    except:
	pass

    Logger.info(whoami() +': kill subprocesses at exit')
    for proc in procs:
	try:
            proc.kill()
	except:
	    pass

    send_command('pkill omxplayer')
    send_command('pkill dbus-daemon')


# ###############################################################
#
# Classes
#
# ###############################################################

class MyListViewLabel(Label):
    pass


class MyAccountCallback(pj.AccountCallback):
    "Callback to receive events from account"
    def __init__(self, account=None):
        pj.AccountCallback.__init__(self, account)


    # Notification on incoming call
    def on_incoming_call(self, call):
        global current_call, mainLayout

	Logger.trace(whoami() +': DND mode = '+ str(mainLayout.dnd_mode))

        if current_call or mainLayout.dnd_mode:
            call.answer(486, "Busy")
            return

        Logger.info(whoami() +": Incoming call from " + call.info().remote_uri)
        current_call = call

        call_cb = MyCallCallback(current_call)
        current_call.set_callback(call_cb)

        current_call.answer(180)


class MyCallCallback(pj.CallCallback):
    "Callback to receive events from Call"

    sip_call_id_last = '***'
    callTimerEvent = None
    CALL_TIMEOUT = 60 * 3

    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)


    def on_state(self):
	"Notification when call state has changed"
        global current_call, ring_event, transparency_value
        global main_state, mainLayout, docall_button_global

	ci = self.call.info()
	if ci.role == 0: role = 'CALLER'
	else: role = 'CALLEE'

	Logger.info('pjSip on_state: Call width=%s is %s (%d) last code=%d (%s) as role=%s'\
	    % (ci.remote_uri, ci.state_text, ci.state, ci.last_code, ci.last_reason, role))
	Logger.debug('pjSip on_state: sip_call_id='+ci.sip_call_id+'  outgoing call='\
	    + str(mainLayout.outgoingCall) + ' current call='+str(current_call))

        main_state = ci.state
        transparency_value = 0

        if main_state == pj.CallState.EARLY:
	    mainLayout.findTargetWindow(ci.remote_uri)
	    if not ring_event and not mainLayout.outgoingCall:
		ring_event = Clock.schedule_interval(playWAV, 3.5)
		playWAV(3.5)
        else:
	    if ring_event:
		Clock.unschedule(ring_event)
		ring_event = None
		stopWAV()

	if self.sip_call_id_last is ci.sip_call_id:
	    Logger.error('pjSip '+whoami()+': Unwanted message='+ci.state_text+' from '+ci.remote_uri+' as '+role)
	    return

	if self.callTimerEvent is None:
	    Clock.unschedule(self.callTimerEvent)
	    self.callTimerEvent = Clock.schedule_once(self.callTimerWD, self.CALL_TIMEOUT)

        if main_state == pj.CallState.INCOMING or main_state == pj.CallState.EARLY:
	    if not mainLayout.outgoingCall:
		docall_button_global.color = COLOR_ANSWER_CALL
		docall_button_global.text = BUTTON_CALL_ANSWER
	    mainLayout.setButtons(True)
	    mainLayout.finishScreenTiming()

        if main_state == pj.CallState.DISCONNECTED:
            current_call = None
	    mainLayout.setButtons(False)
            docall_button_global.color = COLOR_NOMORE_CALL
            docall_button_global.text = BUTTON_DO_CALL
	    mainLayout.startScreenTiming()
	    mainLayout.showPlayers()
	    mainLayout.outgoingCall = False
	    self.sip_call_id_last = ci.sip_call_id
	    if not self.callTimerEvent is None:
		Clock.unschedule(self.callTimerEvent)
		self.callTimerEvent = None

        if main_state == pj.CallState.CONFIRMED:
            docall_button_global.color = COLOR_HANGUP_CALL
            docall_button_global.text = BUTTON_CALL_HANGUP
	    Logger.info('pjSip call status:' + self.call.dump_status())

        if main_state == pj.CallState.CALLING:
	    if not current_call is None:
		Logger.warning('pjSip bad call: CALLING state %s <<>> %s' %(str(current_call), str(self.call)))
		self.call.hangup()
		return
	    current_call = self.call
            docall_button_global.color = COLOR_ANSWER_CALL
            docall_button_global.text = BUTTON_CALL_HANGUP


    def on_media_state(self):
	"Notification when call's media state has changed"
        global mainLayout

        if self.call.info().media_state == pj.MediaState.ACTIVE:
            # Connect the call to sound device
            call_slot = self.call.info().conf_slot
	    try:
        	pj.Lib.instance().conf_connect(call_slot, 0)
        	pj.Lib.instance().conf_connect(0, call_slot)
        	Logger.debug("pjSip "+whoami()+": Media is now active")
	    except pj.Error, e:
        	Logger.error("pjSip "+whoami()+": Media is inactive due to ERROR: " + str(e))
		mainLayout.mediaErrorFlag = True
        else:
            Logger.debug("pjSip "+whoami()+": Media is inactive")
	    mainLayout.mediaErrorFlag = False


    def callTimerWD(self, dt):
	"SIP call watch dog"
        global current_call, ring_event
        global main_state, mainLayout, acc

	Logger.warning(whoami()+':')

	self.callTimerEvent = None
	main_state = pj.CallState.DISCONNECTED
	mainLayout.setButtons(False)
        docall_button_global.color = COLOR_NOMORE_CALL
        docall_button_global.text = BUTTON_DO_CALL
	mainLayout.startScreenTiming()
	mainLayout.showPlayers()
	mainLayout.outgoingCall = False

	if not ring_event is None:
	    Clock.unschedule(ring_event)
	    ring_event = None
	    stopWAV()

	if not current_call is None:
	    try:
		if current_call.is_valid(): current_call.hangup()
	    except:
		pass
	    current_call = None

#	App.get_running_app().stop()


def make_call(uri):
    "Function to make outgoing call"
    global acc

    Logger.debug(whoami() + ': ' + uri)

    try:
	if acc != None: return acc.make_call(uri, cb=MyCallCallback(pj.CallCallback))
    except pj.Error, e:
        Logger.error("pjSip "+whoami()+" Exception: " + str(e))

    return None


# ##############################################################################

class BasicDisplay:
    "basic screen class"
    def __init__(self,winpos,servaddr,sipcall,streamaddr,relaycmd):
	"display area init"
	self.screenIndex = len(procs)
	self.winPosition = winpos.split(',')
	self.winPosition = [int(i) for i in self.winPosition]
	self.serverAddr = str(servaddr)
	self.sipcall = str(sipcall)
	self.streamUrl = str(streamaddr)
	self.relayCmd = str(relaycmd)
	self.playerPosition = [i for i in self.winPosition]

	delta = 2
	self.playerPosition[0] += delta
	self.playerPosition[1] += delta
	self.playerPosition[2] -= delta
	self.playerPosition[3] -= delta
	self.playerPosition = [str(i) for i in self.playerPosition]

	procs.append(self.initPlayer())

	self.color = None
	self.frame = None
	self.actScreen = mainLayout.ids.camera

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

	Logger.debug(whoami()+':')

	return subprocess.Popen(['omxplayer', '--live', '--no-osd',\
	    '--dbus_name',DBUS_PLAYERNAME + str(self.screenIndex),\
	    '--layer', '1', '--no-keys', '--win', ','.join(self.playerPosition), self.streamUrl],\
	    stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE) #, close_fds = True)


    def resizePlayer(self,newpos=''):
	"resize video player area"
	global mainLayout, scr_mode

	Logger.debug(whoami() + ': ' + newpos)

	self.hidePlayer()

	if scr_mode == 1: return

	pos = []
	if not len(newpos): pos = self.playerPosition
	else: pos = newpos.split(',')

        if not send_dbus(DBUS_PLAYERNAME + str(self.screenIndex), ['setvideopos'] + pos):
	    mainLayout.restart_player_window(self.screenIndex)


    def hidePlayer(self):
	"hide video player area"

	Logger.debug(whoami()+':')

	if self.color is not None: self.actScreen.canvas.remove(self.color)
	if self.frame is not None: self.actScreen.canvas.remove(self.frame)

	self.color = None
	self.frame = None


    def setActive(self, active=True):
	"add or remove active flag"
	global current_call

	Logger.debug(whoami()+': index=%d active=%d' % (self.screenIndex, active))

	self.hidePlayer()

	if current_call: return

	if active:
	    self.color = ACTIVE_DISPLAY_BACKGROUND
	else:
	    self.color = INACTIVE_DISPLAY_BACKGROUND

	w = self.winPosition[2] - self.winPosition[0] # width
	h = self.winPosition[3] - self.winPosition[1] # height
	ltx = self.winPosition[0]
	lty = 480 - self.winPosition[1] - h           # touch position is from bottom to up

	self.frame = Rectangle(pos=(ltx, lty), size=(w, h))
	self.actScreen.canvas.add(self.color)
	self.actScreen.canvas.add(self.frame)


    def printInfo(self):
	"print class info"
	Logger.debug('Display: id=%d area=%s IP=%s SIPcall=%s stream=%s'\
	    % (self.screenIndex, self.playerPosition, self.serverAddr, self.sipcall, self.streamUrl))


# ##############################################################################

class Indoor(FloatLayout):

    lib = None
    outgoingCall = False
    dnd_mode = False
    appRestartEvent = None
    mediaErrorFlag = False

    def __init__(self, **kwargs):
	"app init"
        global BUTTON_DO_CALL, BUTTON_CALL_ANSWER, BUTTON_CALL_HANGUP
        global BUTTON_DOOR_1, BUTTON_DOOR_2
	global APP_NAME, SCREEN_SAVER, BRIGHTNESS, WATCHES, RING_TONE
        global main_state, docall_button_global, mainLayout, scrmngr, config

        super(Indoor, self).__init__(**kwargs)

	mainLayout = self

	self.testPlayerIdx = 0
	self.loseNextTouch = False

	self.displays = []

	self.screenTimerEvent = None

        main_state = 0
        self.info_state = 0
        self.myprocess = None

	self.scrmngr = self.ids._screen_manager
	scrmngr = self.scrmngr
	self.sipServerAddr = ''

        # nacitanie konfiguracie
        try:
	    APP_NAME = config.get('about', 'app_name')
        except:
            Logger.warning('Indoor init: ERROR 3 = read config file!')

	watches.APP_LABEL = APP_NAME

        try:
	    value = config.get('command', 'watches').strip()
	    if value in 'analog' or value in 'digital': WATCHES = value
	    else: WATCHES = 'None'
        except:
            Logger.warning('Indoor init: ERROR 4 = read config file!')

        try:
	    screen_saver = config.getint('command', 'screen_saver')
	    if screen_saver > 0 and screen_saver < 120: SCREEN_SAVER = screen_saver * 60
        except:
            Logger.warning('Indoor init: ERROR 5 = read config file!')

        try:
	    self.dnd_mode = config.getint('command', 'dnd_mode') > 0
        except:
            Logger.warning('Indoor init: ERROR 6 = read config file!')

        try:
	    br = config.getint('command', 'brightness')
	    if br > 0 and br < 256: BRIGHTNESS = int(br * 2.55)
        except:
            Logger.warning('Indoor init: ERROR 7 = read config file!')
	    BRIGHTNESS = 255

	send_command(BRIGHTNESS_SCRIPT + ' ' + str(BRIGHTNESS))

        try:
	    RING_TONE = config.get('devices', 'ringtone').strip()
        except:
            Logger.warning('Indoor init: ERROR 11 = read config file!')
	    RING_TONE = 'oldphone.wav'

	itools.PHONERING_PLAYER = APLAYER + ' ' + APARAMS + RING_TONE

        try:
            BUTTON_DO_CALL = config.get('gui', 'btn_docall')
            BUTTON_CALL_ANSWER = config.get('gui', 'btn_call_answer')
            BUTTON_CALL_HANGUP = config.get('gui', 'btn_call_hangup')
            BUTTON_DOOR_1 = config.get('gui', 'btn_door_1')
            BUTTON_DOOR_2 = config.get('gui', 'btn_door_2')
        except:
            Logger.warning('Indoor init: ERROR 8 = read config file!')

        self.ids.btnDoor1.text = BUTTON_DOOR_1
        self.ids.btnDoor1.color = COLOR_BUTTON_BASIC
        self.ids.btnDoor2.text = BUTTON_DOOR_2
        self.ids.btnDoor2.color = COLOR_BUTTON_BASIC
        docall_button_global = self.ids.btnDoCall
        docall_button_global.text = BUTTON_DO_CALL
        docall_button_global.color = COLOR_BUTTON_BASIC

	self.infoText = self.ids.txtBasicLabel

        self.init_myphone()

	self.init_screen()

        self.infinite_event = Clock.schedule_interval(self.infinite_loop, 6.9)
        Clock.schedule_interval(self.info_state_loop, 10.)


    def init_screen(self):
	"define app screen"
	global config, scr_mode

	Logger.debug(whoami()+':')

	scr_mode = 0
	try:
	    scr_mode = config.getint('gui', 'screen_mode')
	except:
            Logger.warning('Indoor init_screen: ERROR 9 = read config file!')
	    scr_mode = 0

	if scr_mode == 1:
	    wins = ['0,0,800,432']
	elif scr_mode == 2:
	    wins = ['0,0,800,216', '0,216,800,432']
	elif scr_mode == 3:
	    wins = ['0,0,400,432', '400,0,800,432']
	else:
	    wins = ['0,0,400,216', '400,0,800,216', '0,216,400,432', '400,216,800,432']

	for i in range(0,len(wins)):
	    win = wins[i]
	    serv = config.get('common', 'server_ip_address_'+str(i + 1)).strip()
	    sipc = config.get('common', 'sip_call'+str(i + 1)).strip()
	    vid = config.get('common', 'server_stream_'+str(i + 1)).strip()
	    relay = 'http://' + serv + '/cgi-bin/remctrl.sh?id='
#	    try:
#		relay = config.get('common', 'server_relay_'+str(i + 1)).strip()
#	    except:
#        	Logger.warning('Indoor init_screen: ERROR 12 = read config file!')
#		relay = 'http://' + serv + '/cgi-bin/remctrl.sh?id='
#
#	    self.dbg(whoami() + ' relay: ' + str(relay))

	    displ = BasicDisplay(win,serv,sipc,vid,relay)
	    self.displays.append(displ)

	self.scrmngr.current = CAMERA_SCR
	self.setButtons(False)

	self.displays[0].setActive()


    def init_myphone(self):
	"sip phone init"
        global acc, config

	Logger.debug(whoami()+':')

        # Create library instance
        lib = pj.Lib()
	self.lib = lib

	accounttype = 'peer-to-peer'
	try:
	    accounttype = config.get('sip', 'sip_mode').strip()
	except:
            Logger.warning('Indoor init_myphone: ERROR 10 = read config file!')

        try:
            # Init library with default config and some customized logging config
            lib.init(log_cfg = pj.LogConfig(level=LOG_LEVEL, callback=log_cb),\
		    media_cfg=setMediaConfig())

	    comSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    comSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	    # bug fix: bad PJSIP start - port in use with another process
	    send_command('pkill dbus-daemon')
	    send_command("netstat -tulpn | grep :5060 | awk '{print $6}' | sed -e 's/\\//\\n/g' | awk 'NR==1 {print $1}' | xargs kill -9")

	    # Create UDP transport which listens to any available port
	    transport = lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(5060))

            # Start the library
            lib.start()

	    cl = lib.enum_codecs()
	    for c in cl:
		Logger.debug(whoami() + ' CODEC ' + c.name + ' priority ' + str(c.priority))

	    # Create local account
	    if accounttype in 'peer-to-peer':
        	acc = lib.create_account_for_transport(transport, cb=MyAccountCallback())
		self.sipServerAddr = ''
	    else:
		s = str(config.get('sip', 'sip_server_addr')).strip()
		u = str(config.get('sip', 'sip_username')).strip()
		p = str(config.get('sip', 'sip_p4ssw0rd')).strip()
		self.sipServerAddr = s

		acc_cfg = pj.AccountConfig(domain=s, username=u, password=p)
#		acc_cfg = pj.AccountConfig()
#		acc_cfg.id = "sip:" + u + "@" + s
#		acc_cfg.reg_uri = "sip:" + s + ":5060"
#		acc_cfg.proxy = [ "sip:" + s + ";lr" ]
#		acc_cfg.auth_cred = [pj.AuthCred("*", u, p)]

		acc = lib.create_account(acc_cfg)
		cb = MyAccountCallback(acc)
		acc.set_callback(cb)

	    Logger.info(whoami()+': Listening on %s port %d Account type=%s SIP server=%s'\
		% (transport.info().host, transport.info().port, accounttype, self.sipServerAddr))

        except pj.Error, e:
            Logger.critical("pjSip Exception: " + e.output)

            lib.destroy()
            self.lib = lib = None


    def info_state_loop(self, dt):
	"state loop"
        global current_call, docall_button_global, BUTTON_DO_CALL, COLOR_BUTTON_BASIC

#	Logger.debug(whoami()+': call='+str(current_call)+' state='+str(self.info_state))

        if not current_call is None: self.info_state = 0

        if self.info_state == 0:
            if current_call is None: self.info_state = 1
        elif self.info_state == 1:
            self.info_state = 2
	    # test if player is alive:
	    if self.scrmngr.current in CAMERA_SCR: val = 255
	    else: val = 0
            if not send_dbus(DBUS_PLAYERNAME + str(self.testPlayerIdx), TRANSPARENCY_VIDEO_CMD + [str(val)]):
		self.restart_player_window(self.testPlayerIdx)
	    self.testPlayerIdx += 1
	    self.testPlayerIdx %= len(self.displays)
        elif self.info_state == 2:
            self.info_state = 0
	    if self.scrmngr.current in CAMERA_SCR:
		docall_button_global.text = BUTTON_DO_CALL
		if self.dnd_mode: docall_button_global.text = BUTTON_DO_CALL + ' (DND)'
		docall_button_global.color = COLOR_BUTTON_BASIC
		self.setButtons(False)


    def infinite_loop(self, dt):
	"main neverendig loop"
        global current_call, active_display_index, procs

	if len(procs) == 0: return

	for idx, p in enumerate(procs):
	    if p.poll() is not None:
#		Logger.debug( "Process" + str(idx) + " (" + str(p.pid) + ") is dead" )
		try:
		    p.kill()
		except:
		    pass
		if current_call is None or idx == active_display_index:
		    procs[idx] = self.displays[idx].initPlayer()


    def startScreenTiming(self):
	"start screen timer"
	global SCREEN_SAVER

        Logger.debug('ScrnEnter: screen saver at %d sec' % SCREEN_SAVER)

	if self.screenTimerEvent: Clock.unschedule(self.screenTimerEvent)
        if SCREEN_SAVER > 0:
	    self.screenTimerEvent = Clock.schedule_once(self.return2clock, SCREEN_SAVER)

	send_command(UNBLANK_SCRIPT)
	send_command(BACK_LIGHT_SCRIPT + ' 0')


    def return2clock(self, *args):
	"swap screen to CLOCK"
	global current_call, WATCHES

        Logger.info(whoami() + ': %s --> %s' % (self.scrmngr.current, WATCHES))

        Clock.unschedule(self.screenTimerEvent)
	self.screenTimerEvent = None

	if current_call is None and self.scrmngr.current in CAMERA_SCR:
	    if WATCHES in 'analog':
		self.scrmngr.current = WATCH_SCR
	    else:
		self.scrmngr.current = DIGITAL_SCR
	    if WATCHES in 'None': send_command(BACK_LIGHT_SCRIPT + ' 1')


    def finishScreenTiming(self):
	"finist screen timer"

        Logger.debug('ScrnLeave: ')

        Clock.unschedule(self.screenTimerEvent)
	self.screenTimerEvent = None


    def swap2camera(self):
	"swap screen to CAMERA"

        Logger.info(whoami()+':')

	self.on_touch_up(None)
	self.scrmngr.current = CAMERA_SCR


    def enterCameraScreen(self):
	"swap screen to CAMERA"
	global current_call

        Logger.debug(whoami() + ': call=' + str(current_call))

	if current_call is None: self.showPlayers()


    def callback_btn_docall(self):
	"make outgoing call"
        global current_call, active_display_index, docall_button_global, BUTTON_DO_CALL
	global ring_event

	Logger.info(whoami() + ': call=' + str(current_call) + ' state=' + str(main_state) +\
	    ' outgoing=' + str(self.outgoingCall))

	if len(procs) == 0: return

        if current_call:
	    Logger.info(whoami() + ' call state: ' + str(current_call.dump_status()))

            if current_call.is_valid() and main_state == pj.CallState.EARLY:
		if not ring_event is None: Clock.unschedule(ring_event)
		ring_event = None
                stopWAV()

		if not self.outgoingCall:
        	    current_call.answer(200)
		else:
		    current_call.hangup()
            else:
                if current_call.is_valid(): current_call.hangup()
		current_call = None
		self.outgoingCall = False
		docall_button_global.text = BUTTON_DO_CALL
		docall_button_global.color = COLOR_BUTTON_BASIC
		self.setButtons(False)
	else:
	    target = self.displays[active_display_index].sipcall

	    if len(target) == 0: return

	    if len(self.sipServerAddr) and '.' not in target:
		target = target + '@' + self.sipServerAddr

	    lck = self.lib.auto_lock()
	    self.outgoingCall = True
	    if make_call('sip:' + target + ':5060') is None:
		if self.mediaErrorFlag:
		    txt = 'Audio ERROR'
		else:
		    txt = '--> ' + str(active_display_index + 1) + ' ERROR'
		docall_button_global.color = COLOR_ERROR_CALL
		docall_button_global.text = txt
	    else:
		self.setButtons(True)
	    del lck


    def gotResponse(self, req, results):
	"relay result"
        Logger.debug('Relay: req=' + str(req) + ' res=' + results)


    def setRelayRQ(self, relay):
	"send relay request"
        global active_display_index

        Logger.trace('SetRelay: ' + relay)

	if len(procs) == 0: return

        req = UrlRequest(self.displays[active_display_index].relayCmd + relay,\
                on_success = self.gotResponse, timeout = 5)


    def callback_btn_door1(self):
	"door 1 button"
        Logger.debug(BUTTON_DOOR_1+':')
        self.setRelayRQ('relay1')


    def callback_btn_door2(self):
	"door 2 button"
        Logger.debug(BUTTON_DOOR_2+':')
        self.setRelayRQ('relay2')


    def callback_set_options(self):
	"start settings"

        Logger.debug(whoami() + ": " + self.ids.btnSetOptions.text)

#	self.hidePlayers()

#        Popup(title="Enter password",
#              content=TextInput(focus=True),
#              size_hint=(0.6, 0.6),
#              on_dismiss=self.openAppSettings).open()

	self.scrmngr.current = SETTINGS_SCR
	App.get_running_app().open_settings()


#    def openAppSettings(self, popup):
#	"swap to Settings screen"
#	Logger.debug(whoami() + ': ' + popup.content.text)
#
#	if popup.content.text in '1234':
#	    self.scrmngr.current = SETTINGS_SCR
#	    App.get_running_app().open_settings()
#	else:
#	    self.showPlayers()


    def callback_set_voice(self, value):
	"volume buttons"
	global AUDIO_VOLUME, current_call

	Logger.debug(whoami() + ': value=' + str(value) + ' btnTxt=' + self.ids.btnScreenClock.text)

	if current_call is None:
	    if value == 1:
		self.callback_set_options()
	    else:
		Clock.schedule_once(self.return2clock, .2)
	else :
	    vol = AUDIO_VOLUME + int(value) * 20
	    if vol > 80: vol = 100
	    elif vol > 60: vol = 80
	    elif vol > 40: vol = 60
	    elif vol > 20: vol = 40
	    else: vol = 20
	    AUDIO_VOLUME = vol

	    self.ids.btnScreenClock.disabled = vol < 40
	    self.ids.btnSetOptions.disabled = vol > 80

	    send_command(SETVOLUME_SCRIPT + ' ' + str(AUDIO_VOLUME))


    def restart_player_window(self, idx):
	"process is bad - restart"

	Logger.info(whoami()+': idx='+str(idx))

	self.displays[idx].hidePlayer()
	send_command("ps aux | grep omxplayer"+str(idx)+" | grep -v grep | awk '{print $2}' | xargs kill -9")
	send_command(CMD_KILL + str(procs[idx].pid))


    def supporter1(self, dt):
	"clear restart flag"
	Logger.debug(whoami()+ ': clear restart flag')
	self.appRestartEvent = None


    def checkTripleTap(self,touch):
	"check if triple tap is in valid area, if yes -> finish app"

	Logger.info(whoami()+':')

	x = touch.x
	y = touch.y
	if x < 50 and y > 430:
	    if self.appRestartEvent is None:
		self.appRestartEvent = Clock.schedule_once(self.supporter1, 5.)
	    else:
		Clock.unschedule(self.appRestartEvent)
		self.appRestartEvent = None

	if x > 730 and y > 430 and not self.appRestartEvent is None:
	    Logger.error(whoami() + ': valid triple tap -> restart')
	    App.get_running_app().stop()


    def on_touch_up(self, touch):
	"process touch up event"
	global active_display_index, current_call

	Logger.info(whoami()+': loseNext='+str(self.loseNextTouch))
	if not touch is None:
	    Logger.debug(whoami()+': touch=%d,%d double=%d triple=%d'\
		% (touch.x, touch.y, touch.is_double_tap, touch.is_triple_tap))

	if self.loseNextTouch:
	    self.loseNextTouch = False
	    return

#	if not self.collide_point(*touch.pos): return
#	print whoami(), self.collide_point(*touch.pos)

	if len(procs) == 0: return

	if not touch is None and touch.is_triple_tap:
	    self.checkTripleTap(touch)

	if not touch is None and touch.is_double_tap:
	    if not current_call and self.scrmngr.current in CAMERA_SCR:
		self.restart_player_window(active_display_index)
	    return

	if current_call is None: self.startScreenTiming()

#	for child in self.walk():
#	    if child is self: continue
#	    if child.collide_point(*touch.pos):
#		print 'HUHUHUUUUUUUUUUU', touch.x, touch.y
#		return

	if touch is None:
	    self.loseNextTouch = True
	    return

	if not self.scrmngr.current in CAMERA_SCR or not current_call is None: return

	rx = int(round(touch.x))
	ry = int(round(touch.y))

	for idx, d in enumerate(self.displays):
	    t = d.testTouchArea(rx, ry)
	    if t:
		active_display_index = idx
	    else:
		d.setActive(False)

	self.displays[active_display_index].setActive()


    def showPlayers(self):
	"d-bus command to show video"

	Logger.debug(whoami()+': ')

	for idx, proc in enumerate(procs):
	    if not send_dbus(DBUS_PLAYERNAME + str(idx), TRANSPARENCY_VIDEO_CMD + [str(255)]):
		self.restart_player_window(idx)

	self.displays[active_display_index].resizePlayer()
	self.infoText.text = ''
	self.displays[active_display_index].setActive()


    def worker1(self):
	"thread - hide video"
	for idx, proc in enumerate(procs):
	    self.displays[idx].hidePlayer()
	    if not send_dbus(DBUS_PLAYERNAME + str(idx), TRANSPARENCY_VIDEO_CMD + [str(0)]):
		self.restart_player_window(idx)


    def hidePlayers(self):
	"d-bus command to hide video"
	Logger.debug(whoami()+': ')

	Thread(target=self.worker1).start()


    def setButtons(self, visible):
	"set buttons (ScrSaver, Options, Voice+-) to accurate state"
	global AUDIO_VOLUME

	Logger.debug(whoami()+': ')

	if visible:
	    self.ids.btnScreenClock.text = '-'
	    self.ids.btnSetOptions.text = '+'
	    self.ids.btnScreenClock.disabled = AUDIO_VOLUME < 40
	    self.ids.btnSetOptions.disabled = AUDIO_VOLUME > 80
	else:
	    self.ids.btnScreenClock.text = 'C'
	    self.ids.btnSetOptions.text = 'S'
	    self.ids.btnScreenClock.disabled = False
	    self.ids.btnSetOptions.disabled = False


    def findTargetWindow(self, addr):
	"find target window according to calling address"
	global active_display_index

        Logger.info('find target window: address=' + addr)

	ret = False
	self.infoText.text = addr

	if addr != '':
	    active_display_index = 0
	    for idx, d in enumerate(self.displays):
		d.setActive(False)
		d.hidePlayer()
		if not ret and d.sipcall in addr and d.sipcall != '':
		    active_display_index = idx
		    self.infoText.text = d.sipcall
		    d.resizePlayer('80,10,720,390')
		    ret = True
		else:
        	    if not send_dbus(DBUS_PLAYERNAME + str(idx), TRANSPARENCY_VIDEO_CMD + [str(0)]):
			self.restart_player_window(idx)

	if ret and not self.scrmngr.current in CAMERA_SCR:
	    if not send_dbus(DBUS_PLAYERNAME + str(active_display_index), TRANSPARENCY_VIDEO_CMD + [str(255)]):
		self.restart_player_window(active_display_index)

	self.scrmngr.current = CAMERA_SCR

	return ret


# ###############################################################

class IndoorApp(App):

    restartAppFlag = False

    def build(self):
	global config

        Logger.warning('Hello Indoor 2.0')

	self.config = config

	kill_subprocesses()

##        Config.set('kivy', 'keyboard_mode','')
        Logger.debug('Configuration: keyboard_mode=%r, keyboard_layout=%r'\
	    % (Config.get('kivy', 'keyboard_mode'), Config.get('kivy', 'keyboard_layout')))

	self.settings_cls = SettingsWithSidebar
        self.use_kivy_settings = False

	self.changeInet = False
	self.get_volume_value()

	return Indoor()


#    def on_start(self):
#        self.dbg(whoami())
#
#    def on_stop(self):
#        self.dbg(whoami())
#	self.root.stop.set()


    def build_config(self, cfg):
	"build config"
	global config

        Logger.debug(whoami()+': ')

	config.setdefaults('command', {
	    'screen_saver': 1,
	    'dnd_mode': 0,
	    'brightness': 100,
	    'watches': 'analog' })
	config.setdefaults('sip', {
	    'sip_mode': 'peer-to-peer',
	    'sip_server_addr': '',
	    'sip_username': '',
	    'sip_p4ssw0rd': '' })
	config.setdefaults('devices', {
	    'sound_device_in': '',
	    'sound_device_out': '',
	    'ringtone': 'oldphone.wav',
	    'volume': 100 })
	config.setdefaults('gui', {
	    'screen_mode': 0,
	    'btn_docall': 'Do Call',
	    'btn_call_answer': 'Answer Call',
	    'btn_call_hangup': 'HangUp Call',
	    'btn_door_1': 'Open Door 1',
	    'btn_door_2': 'Open Door 2' })
	config.setdefaults('common', {
	    'server_ip_address_1': '192.168.1.250',
	    'server_stream_1': 'http://192.168.1.250:80/video.mjpg',
	    'sip_call1': '',
	    'server_ip_address_2': '',
#	    'server_stream_2': 'http://192.168.1.241:8080/stream/video.mjpeg',
	    'server_stream_2': '',
	    'sip_call2': '',
	    'server_ip_address_3': '',
#	    'server_stream_3': 'http://192.168.1.241:8080/stream/video.mjpeg',
	    'server_stream_3': '',
	    'sip_call3': '',
	    'server_ip_address_4': '',
	    'server_stream_4': '',
	    'sip_call4': '' })

	s = get_info(SYSTEMINFO_SCRIPT).split()
	config.setdefaults('about', {
	    'app_name': 'Indoor 2.0',
	    'app_ver': '2.0.0.0',
	    'serial': s[1] })
	config.set('about', 'serial', s[1])

	dns = ''
	try:
	    dns = s[8]
	except:
	    dns = ''

	config.setdefaults('system', {
	    'inet': s[2],
	    'ipaddress': s[3],
	    'gateway': s[6],
	    'netmask': s[4],
	    'dns': dns })
	config.set('system', 'inet', s[2])
	config.set('system', 'ipaddress', s[3])
	config.set('system', 'gateway', s[6])
	config.set('system', 'netmask', s[4])
	config.set('system', 'dns', dns)


    def get_uptime_value(self):
	"retrieve system uptime"
	with open('/proc/uptime', 'r') as f:
	    uptime_seconds = float(f.readline().split()[0]) or 0
	    uptime_string = str(timedelta(seconds = uptime_seconds))

        Logger.debug(whoami() + ': uptime=' + uptime_string)

	return uptime_string


    def get_volume_value(self):
	"retrieve current volume level"
	global AUDIO_VOLUME

        Logger.debug(whoami()+': ')

	s = get_info(VOLUMEINFO_SCRIPT).split()
	if len(s) < 4:
	    vol = 0		# script problem!
	else:
	    vol = int(round(float(s[1]) / (int(s[3]) - int(s[2])) * 100.0)) or 0

	# available volume steps:
	if vol > 80: vol = 100
	elif vol > 60: vol = 80
	elif vol > 40: vol = 60
	elif vol > 20: vol = 40
	else: vol = 20
	AUDIO_VOLUME = vol

	return vol


    def build_settings(self, settings):
	"display settings screen"
	global config

        Logger.debug(whoami()+': ')

	settings.register_type('buttons', SettingButtons)

	config.set('devices', 'volume', AUDIO_VOLUME)
	config.set('devices', 'ringtone', RING_TONE)

	asystem = settings_system
	"""
	# enable|disable network parameters
	vDhcp = config.get('system', 'inet') in 'dhcp'
	sys = json.loads(settings_system)
	asystem = []
	for s in sys:
	    item = s
	    if s['type'] not in 'title' and s['key'] not in 'inet': item['disabled'] = vDhcp
	    asystem.append(item)
	asystem = json.dumps(asystem)
	"""

	asip = settings_sip
	"""
	# enable|disalbe SIP parameters
	vSip = config.get('sip', 'sip_mode')
	sys = json.loads(settings_sip)
	asip = []
	for s in sys:
	    item = s
	    if s['type'] not in 'title' and s['key'] not in 'sip_mode': item['disabled'] = vSip
	    asip.append(item)
	asip = json.dumps(asip)
	"""

	acomm = settings_outdoor
	"""
	# enable|disalbe players
	wins = config.getint('gui', 'screen_mode')
	if wins == 0 or wins == 4:
	    acomm = settings_outdoor
	elif wins == 1:
	    enabledWin = '1'
	    sys = json.loads(settings_outdoor)
	    acomm = []
	    for s in sys:
		item = s
		if not (s['type'] not in 'title' and enabledWin not in s['key']):
		    acomm.append(item)
	    acomm = json.dumps(acomm)
	else:
	    sys = json.loads(settings_outdoor)
	    acomm = []
	    for s in sys:
		item = s
		if not (s['type'] not in 'title' and ('3' in s['key'] or '4' in s['key'])):
		    acomm.append(item)
	    acomm = json.dumps(acomm)
	"""

        settings.add_json_panel('Application',
                                config,
                                data=settings_app)
        settings.add_json_panel('GUI',
                                config,
                                data=settings_gui)
        settings.add_json_panel('Outdoor Devices',
                                config,
                                data=acomm)
        settings.add_json_panel('Audio Device',
                                config,
                                data=settings_audio)
        settings.add_json_panel('SIP',
                                config,
                                data=asip)
        settings.add_json_panel('Network',
                                config,
                                data=asystem)
        settings.add_json_panel('Service',
                                config,
                                data=settings_services)
        settings.add_json_panel('About',
                                config,
                                data=settings_about)


    def display_settings(self, settings):
	"display settings"
	global mainLayout

        Logger.debug(whoami()+': ')

#        return super(IndoorApp, self).display_settings(settings)
	mainLayout.ids.settings.add_widget(settings)


    def on_config_change(self, cfg, section, key, value):
	"config item changed"
	global config, SCREEN_SAVER, BRIGHTNESS, WATCHES, VOLUME, mainLayout
#	global BUTTON_DO_CALL, BUTTON_CALL_ANSWER, BUTTON_CALL_HANGUP, BUTTON_DOOR_1, BUTTON_DOOR_2

        Logger.info(whoami()+': sec=%s key=%s val=%s' %(section, key, value))
	token = (section, key)
	value = value.strip()

	config.set(section, key, value)
	config.write()

	if section == 'common':
	    self.restartAppFlag = True
	elif token == ('command', 'brightness'):
	    try:
		v = int(value)
		BRIGHTNESS = int(v * 2.55)
	    except:
		BRIGHTNESS = 255
	    send_command(BRIGHTNESS_SCRIPT + ' ' + str(BRIGHTNESS))
	elif token == ('command', 'dnd_mode'):
	    mainLayout.dnd_mode = int(value) > 0
	elif token == ('command', 'screen_saver'):
	    try:
		v = int(value)
		SCREEN_SAVER = v * 60
	    except:
		SCREEN_SAVER = 0
	elif token == ('command', 'watches'):
	    if value in 'analog' or value in 'digital': WATCHES = value
	    else: WATCHES = 'None'
	elif token == ('devices', 'volume'):
	    AUDIO_VOLUME = value
	    send_command(SETVOLUME_SCRIPT + ' ' + str(AUDIO_VOLUME))
	elif token == ('devices', 'ringtone'):
	    RING_TONE = value
	    stopWAV()
	    itools.PHONERING_PLAYER = APLAYER + ' ' + APARAMS + RING_TONE
	    playWAV(3.0)
	elif section in 'system' and (key in ['ipaddress', 'netmask', 'gateway', 'dns']):
	    if config.get('system', 'inet') in 'dhcp':
#		config.set(section, key, self.config.get(section, key))
		config.set(section, key, config.getdefault(section, key))
		config.write()
	    else:
		self.changeInet = True
	elif section in 'sip' and (key in ['sip_server_addr', 'sip_username', 'sip_p4ssw0rd']):
	    if config.get('sip', 'sip_mode') in 'peer-to-peer':
		config.set(section, key, self.config.get(section, key))
#		config.set(section, key, config.getdefault(section, key))
		config.write()
	    else:
		self.changeInet = True
	elif token == ('service', 'buttonpress'):
	    if 'button_status' == value:
		self.myAlertBox('App status', 'uptime: ' + self.get_uptime_value())
	elif token == ('service', 'buttonlogs'):
	    if 'button_loghist' == value:
	        # LoggerHistory.history:
	        recent_log = [('%d %s' % (record.levelno, record.msg)) for record in LoggerHistory.history] #reversed(LoggerHistory.history
		self.myAlertListBox('Log history', recent_log)
	elif token == ('service', 'app_rst'):
	    if 'button_app_rst' == value:
		self.myAlertBox('WARNING', 'Application is going to restart!', self.popupClosed, False)
	elif token == ('system', 'inet'):
	    self.changeInet = True
	elif 'gui' in section or token == ('sip', 'sip_mode'):
	    self.restartAppFlag = True
#	    self.destroy_settings()
#	    self.open_settings()


    def popupClosed(self, popup):
	"restart App after alert box"

        Logger.debug(whoami()+': ')

	kill_subprocesses()

#	send_command('sync')
#	send_command('pkill python')
	App.get_running_app().stop()


    def close_settings(self, *args):
	"close button pressed"
	global scrmngr, mainLayout, config

        Logger.debug(whoami()+': ')

	mainLayout.ids.settings.clear_widgets()

	if self.changeInet or self.restartAppFlag:
	    if self.changeInet: # start script
		send_command(SETIPADDRESS_SCRIPT\
			 + ' ' + config.get('system', 'inet')\
			 + ' ' + config.get('system', 'ipaddress')\
			 + ' ' + config.get('system', 'netmask')\
			 + ' ' + config.get('system', 'gateway')\
			 + ' ' + config.get('system', 'dns'))

	    self.myAlertBox('App info', 'Application is going to restart to apply your changes!', self.popupClosed, False)
	else:
	    self.changeInet = False
	    scrmngr.current = CAMERA_SCR


    def myAlertBox(self, titl, txt, cb=None, ad=True):
	"Alert box"
	global scrmngr

	Logger.debug(whoami()+': title='+titl+' msg='+txt)

	if not cb is None:
	    scrmngr.current = WAIT_SCR
	    txt = txt + '\n\nPress OK'

	box = BoxLayout(orientation='vertical', spacing=10)
	box.add_widget(Label(text=txt, padding_y=80))
	btn = Button(text='OK', size_hint=(1, 0.4))
	box.add_widget(btn)
	p = Popup(title=titl, content=box, size_hint=(0.8, 0.6), auto_dismiss=ad)
	if cb is None: cb = p.dismiss
	btn.bind(on_press=cb)
	p.bind(on_press=cb)
	p.open()


    def myAlertListBox(self, titl, ldata, cb=None, ad=True):
	"Alert box"
	LJUST = 83

	Logger.debug(whoami()+': title='+titl)

	box = BoxLayout(orientation='vertical', spacing=5)

	# text color:
	c = [int(t[:2]) for t in ldata]
	clr = []
	for x in c:
	    y = (1,1,1,1)
	    if x < 11: y = (1,1,1,1)
	    elif x < 21: y = (.5,1,1,1)
	    elif x < 31: y = (.5,.5,1,1)
	    else: y = (1,.5,0,1)
	    clr.append(y)

	# justify text:
	data = [t[:LJUST] + '...' if len(t) > LJUST else t[:] for t in ldata]

	args_converter = lambda row_idx, rec: {'text': rec,
                                            'size_hint_y': None,
					    'color': clr[row_idx],
                                            'height': 25}

	list_adapter = ListAdapter(data=data, cls=MyListViewLabel,
			    args_converter=args_converter,
			    selection_mode='single', allow_empty_selection=True)

	list_view = ListView(adapter=list_adapter)
	box.add_widget(list_view)

	p = Popup(title=titl, content=box, size_hint=(0.85, 0.95), auto_dismiss=ad)
#	if cb is None: cb = p.dismiss
#	p.bind(on_press=cb)
	p.open()


# ###############################################################
#
# Start
#
# ###############################################################

if __name__ == '__main__':
    send_command('./clrscr.sh')
    IndoorApp().run()
