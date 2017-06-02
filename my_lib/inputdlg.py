#!/bin/python

# ###############################################################
#
# Imports
#
# ###############################################################

import kivy
kivy.require('1.9.0')


from kivy.lang import Builder
from kivy.logger import Logger, LoggerHistory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from constants import *
from itools import *


# ###############################################################
#
# Popup Class - input text
#
# ###############################################################

KV = '''
BoxLayout:
    orientation: 'vertical'
    lbl1: lbl1
    tin1: tin1
    btno: btno
    btok: btok
    spacing: '8px'

    Label:
        text: ''
        id: lbl1
        font_size: 20
        size_hint_y: None
        height: '32px'

    TextInput:
        text: ''
        id: tin1
        multiline: False
        size_hint_y: None
        font_size: '24px'
        height: '40px'

    AsyncImage:
        source: 'imgs/nothing.png'

    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: 48
        spacing: '8px'

        Button:
            text: 'OK'
            id: btok
        Button:
            text: 'Cancel'
            id: btno
'''


class MyInputBox(Popup):
    "Input popup box"
    def __init__(self, **kwargs):
        super(MyInputBox, self).__init__(**kwargs)

        Logger.debug('%s: titl=$%s msg=%s' % (whoami(),kwargs.get('titl'),kwargs.get('txt')))

	self.p = Builder.load_string(KV)
	self.p.lbl1.text = kwargs.get('txt') or ''
	self.p.tin1.text = ''
	self.p.tin1.password = kwargs.get('pwd') or False
        self.p.btok.bind(on_press=self.buttonOk)
        self.p.btno.bind(on_press=self.buttonNo)

	self.title = kwargs.get('titl')
	self.auto_dismiss = kwargs.get('ad') or False
	self.cb = kwargs.get('cb') or None
	self.size_hint = (.6, .5)
	self.content = self.p


    def buttonOk(self, b):
        Logger.debug('%s: Yes msg=%s' % (whoami(), self.p.tin1.text))

	self.dismiss()
	if not self.cb is None: self.cb(self.p.tin1.text)


    def buttonNo(self, b):
        Logger.debug('%s: No' % (whoami()))

	self.dismiss()
	if not self.cb is None: self.cb('')


# ##############################################################################
