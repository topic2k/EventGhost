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

PM_NAME = eg.APP_NAME + " Plugin Manager"

PLUGIN_DETAILS_HTML_STYLE = "<style> body, table { margin:4px; " \
                            "font-family:verdana; font-size:12px; " \
                            "} </style>"

info_all = """<h3>All Plugins</h3>
<p>
On the left you see the list of all plugins available for your EventGhost,
both installed and available for download. Some plugins come with your
EventGhost installation while most of them are made available via
the plugin repositories.
</p>

<p>
You can temporarily enable or disable a plugin.
To <i>enable</i> or <i>disable</i> a plugin, click its checkbox
or doubleclick its name...
</p>

<p>
Plugins showing in <span style='color:red'>red</span> are not loaded
because there is a problem. They are also listed on the 'Invalid' tab.
Click on the plugin name to see more details, or to reinstall or
uninstall this plugin.
</p>\
"""
info_installed = """<h3>Installed Plugins</h3>

<p>
Here you only see plugins <b>installed</b> in EventGhost.
</p>
<p>
Click on the name to see details.
</p>
<p>
Click the checkbox or doubleclick the name to <i>activate</i> or
<i>deactivate</i> the plugin.
</p>
<p>
You can change the sorting via the context menu (right click).
</p>
"""
info_not_installed = """<h3>Not installed plugins</h3>

<p>
Here you see the list of all plugins available in the repositories, but
which are <b>not yet installed</b>.
</p>
<p>
Click on the name to see details.
</p>
<p>
You can change the sorting via the context menu (right click).
</p>
<p>
A plugin can be downloaded and installed by clicking on it's name, and
then click the 'Install plugin' button.
</p>
"""
info_upgradeable = """<h3>Upgradeable plugins</h3>

<p>
Here are <b>upgradeable plugins</b>. It means more recent versions of installed
plugins are available in the repositories.
</p>
"""
info_new = """<h3>New plugins</h3>

<p>
Here you see <b>new</b> plugins which were released
since you last visited this list.
</p>
"""
info_invalid = """<h3>Invalid plugins</h3>

<p>
Plugins in this list here are <b>broken or incompatible</b> with your
version of EventGhost.
</p>

<p>
Click on an individual plugin; if possible EventGhost shows
you more information.
</p>

<p>
The main reasons to have invalid plugins is that this plugin is not build
for this version of EventGhost. Maybe you can download another version
from <a href="http://www.eventghost.net/downloads/">www.eventghost.net</a>.
</p>

<p>
Another common reason is that a plugin needs some external python
libraries (dependencies). You can install them yourself, depending on
your operating system. After a correct install, the plugin should work.
</p>
"""


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


VIEWS = {
    "All plugins": {
        "desc": info_all,
        "func": GetAll,
    },
    "Installed plugins": {
        "desc": info_installed,
        "func": GetAllInstalled,
    },
    "Not installed plugins": {
        "desc": info_not_installed,
        "func": GetAllNotInstalled,
    },
    "Upgradeable plugins": {
        "desc": info_upgradeable,
        "func": GetAllUpgradeable,
    },
    "New plugins": {
        "desc": info_new,
        "func": GetAllNew,
    },
    "Invalid plugins": {
        "desc": info_invalid,
        "func": GetAllInvalid,
    },
}
DEFAULT_VIEW = VIEWS.keys()[0]


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
