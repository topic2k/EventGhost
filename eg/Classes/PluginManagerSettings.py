# -*- coding: utf-8 -*-
#
# This file is part of EventGhost.
# Copyright © 2005-2016 EventGhost Project <http://www.eventghost.org/>
#
# EventGhost is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# EventGhost is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with EventGhost. If not, see <http://www.gnu.org/licenses/>.

import eg


egtext = eg.text.PluginManager.Dialog

PLUGIN_DETAILS_HTML_STYLE = "<style> body, table { margin:4px; " \
                            "font-family:verdana; font-size:12px; " \
                            "} </style>"


def GetAll():
    return eg.pluginManager.plugins.GetAll()


def GetAllInstalled():
    return eg.pluginManager.plugins.GetAllInstalled()


def GetAllNotInstalled():
    return eg.pluginManager.plugins.GetAllNotInstalled()


def GetAllUpgradeable():
    return eg.pluginManager.plugins.GetAllUpgradeable()


def GetAllNew():
    return eg.pluginManager.plugins.GetAllNew()


def GetAllInvalid():
    return eg.pluginManager.plugins.GetAllInvalid()


ALL_PLUGINS_LABEL = egtext.LabelAllPlugins
DEFAULT_VIEW = egtext.LabelAllPlugins
VIEWS = {
    egtext.LabelAllPlugins: {
        "desc": egtext.InfoAll.format(eg.APP_NAME),
        "func": GetAll,
    },
    egtext.LabelInstalled: {
        "desc": egtext.InfoInstalled.format(eg.APP_NAME),
        "func": GetAllInstalled,
    },
    egtext.LabelNotInstalled: {
        "desc": egtext.InfoNotInstalled,
        "func": GetAllNotInstalled,
    },
    egtext.LabelUpgradeable: {
        "desc": egtext.InfoUpgradeable,
        "func": GetAllUpgradeable,
    },
    egtext.LabelNew: {
        "desc": egtext.InfoNew,
        "func": GetAllNew,
    },
    egtext.LabelInvalid: {
        "desc": egtext.InfoInvalid.format(eg.APP_NAME),
        "func": GetAllInvalid,
    },
}


# noinspection PyClassHasNoInit
class Config(eg.PersistentData):
    allow_deprecated = False
    allow_experimental = False
    check_interval = 0  # allowed values: 0,1,3,7,14,30 days
    check_on_start = True
    last_start = None  # ISO formated date string
    repositories = []
    seen_plugins = []  # TODO: empty list on EG exit and/or daily?
    #                          other way to handle it?
