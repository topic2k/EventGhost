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

import os
import os.path
import shutil
import sys
import tempfile
import xml.parsers.expat
from copy import copy
from os.path import exists, isdir, join
from zipfile import BadZipfile

import requests
import wx
import wx.html
import wx.html2
import wx.lib.agw.infobar as IB
import wx.lib.agw.ultimatelistctrl as ULC
import wx.lib.newevent
import wx.richtext
import xmltodict
from pkg_resources import parse_version
from wx.lib.splitter import MultiSplitterWindow

import eg

PM_NAME = eg.APP_NAME + " Plugin Manager"

OFFICIAL_REPO = {
    # human readable repository name
    "name": "Official EventGhost Plugin Repository",

    # current repository url
    # http://eg-plugins.torsti.net/egplugins/plugins.php",
    "url": "http://diskstation/~topic/egplugins/plugins.php",

    # list of deprecated repository urls
    "deprecated": (
        "http://diskstation/~topic/plugins/plugins.php",
        "http://egplugins.torsti.net/plugins/plugins.php"
    ),
}
TRANSLATABLE_ATTRIBUTES = [
    "name", "description", "longDescription",
    "pluginHelp", "kind"
]

REPO_STATE_DISABLED = 0
REPO_STATE_LOADING = 1
REPO_STATE_LOADED_OK = 2
REPO_STATE_REQ_FETCHING = 3
REPO_STATE_REJECTED = 4
REPO_STATE_ERROR = 5  # to be retrieved (3)

UPDATE_CHECK_INTERVAL = [0, 1, 3, 7, 14, 30]
UPDATE_CHECK_CHOICES = [
    "on every call of PluginManager",
    "once a day",
    "every 3 days",
    "every week",
    "every 2 weeks",
    "every month"
]

ID_REPO_LIST = wx.ID_HIGHEST + 1
ID_REPO_RELOAD = wx.ID_HIGHEST + 2
ID_REPO_ADD = wx.ID_HIGHEST + 3
ID_REPO_EDIT = wx.ID_HIGHEST + 4
ID_REPO_DELETE = wx.ID_HIGHEST + 5
ID_VIEW = wx.ID_HIGHEST + 6
ID_PLUGIN_LIST = wx.ID_HIGHEST + 7
ID_PLUGIN_FILTER = wx.ID_HIGHEST + 8
ID_UPGRADE_ALL = wx.ID_HIGHEST + 9
ID_UNINSTALL = wx.ID_HIGHEST + 10
ID_INSTALL = wx.ID_HIGHEST + 11
ID_PLUGIN_DETAILS = wx.ID_HIGHEST + 12
ID_INTERVALL = wx.ID_HIGHEST + 13
ID_EXPERIMENTAL = wx.ID_HIGHEST + 14
ID_DEPRECATED = wx.ID_HIGHEST + 15
ID_UPDATE_CHECK = wx.ID_HIGHEST + 16

LB_SORT_ASCENDING = 1
LB_SORT_DESCENDING = 2
LB_SORT_BY_NAME = 4
LB_SORT_BY_DOWNLOADS = 8
LB_SORT_BY_VOTE = 16
LB_SORT_BY_STATUS = 32
LB_SORT_BY_RELEASE_DATE = 64

tabInfoHTML = "<style> body, table { margin:4px; " \
              "font-family:verdana; font-size:12px; " \
              "} </style>"
tabDescriptions = [
    # must match the choices in ListBox
    # 0 = all plugins
    # 1 = installed plugins
    # 2 = not installed plugins
    # 3 = upgradeable plugins
    # 4 = new plugins
    # 5 = invalid plugins

######  all_plugins  #####
"""<h3>All Plugins</h3>
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
""",

#####  installed plugins  #####
"""<h3>Installed Plugins</h3>

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
""",

#####  not installed plugins  #####
"""<h3>Not installed plugins</h3>

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
""",

#####  upgradeable plugins  #####
"""<h3>Upgradable plugins</h3>

<p>
Here are <b>upgradeable plugins</b>. It means more recent versions of installed
plugins are available in the repositories.
</p>
""",

#####  new plugins  #####
"""<h3>New plugins</h3>

<p>
Here you see <b>new</b> plugins which were released
since you last visited this list.
</p>
""",

#####  invalid plugins  #####
"""<h3>Invalid plugins</h3>

<p>
Plugins in this list here are <b>broken or incompatible</b> with your
version of EventGhost.
</p>

<p>
Click on an individual plugin; if possible EventGhost shows you more information.
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
""",
]


CheckingDone, EVT_CHECKING_DONE = wx.lib.newevent.NewEvent()
AnythingChanged, EVT_ANYTHING_CHANGED = wx.lib.newevent.NewEvent()
RepositoryFetched, EVT_REPOSITORY_FETCHED = wx.lib.newevent.NewEvent()


def remove_plugin_dir(path, parent=None):
    if not os.path.exists(path):
        return  # Nothing to remove
    else:
        def onError(function, path, excinfo):
            eg.MessageBox("Removing plugin failed!\n"
                          "Path: {0}\n"
                          "Function: {1}\n"
                          "Exception information:\n{2}"
                          .format(repr(path), repr(function), repr(excinfo)),
                          PM_NAME, parent=parent,
                          style=wx.OK | wx.ICON_ERROR)

        shutil.rmtree(path, onerror=onError)


class Config(eg.PersistentData):
    repositories = []
    #check_on_EG_start = True
    check_on_show_PM = True
    check_interval = 0  # allowed values: 0,1,3,7,14,30 days
    last_start = None  # ISO formated date string
    allow_experimental = False
    allow_deprecated = False
    seen_plugins = []  # TODO: empty list on EG exit and/or daily? other way to handle it?


class PluginManager:
    """
    The main class for managing the plugin installer stuff.
    """
    def __init__(self):
        self.plugins = PluginCache()
        self.InitGUI(None)

    def GetPluginInfoList(self):
        return self.plugins.GetPluginInfoList()

    def GetPluginInfo(self, guid):
        return self.plugins.GetPluginInfo(guid)

    def OpenPlugin(self, ident, evalName, args, treeItem=None):
        moduleInfo = self.plugins.GetPluginInfo(ident)
        if moduleInfo is None:
            # we don't have such plugin
            clsInfo = NonexistentPluginInfo(ident, evalName)
        else:
            try:
                clsInfo = eg.PluginInstanceInfo.FromModuleInfo(moduleInfo)
            except eg.Exceptions.PluginLoadError:
                if evalName:
                    clsInfo = NonexistentPluginInfo(ident, evalName)
                else:
                    raise
        info = clsInfo.CreateInstance(args, evalName, treeItem)
        if moduleInfo is None:
            info.actions = ActionsMapping(info)
        return info

    def ShowPluginManager(self, mainFrame=None):
        self.repositories = Repositories(self.gui, self.plugins)
        self.repositories.FetchRepositories()
        self.LookForObsoletePlugins()
        self.fetchAvailablePlugins(reloadMode=False)
        self.exportRepositoriesToManager()
        self.exportPluginsToManager()
        self.gui.Show()

    def LookForObsoletePlugins(self):
        """
        Look for obsolete plugins.
        (the user-installed one is newer than core one)
        """
        for key in self.plugins.obsolete_plugins:
            plugin = self.plugins.local_cache[key]
            dlg = wx.MessageDialog(
                None,
                "Obsolete plugin:\n{0}".format(plugin["name"]) + "\n\n"
                "EventGhost has detected an obsolete plugin that masks "
                "its more recent version shipped with this copy of "
                "EventGhost. Do you want to remove the old plugin right "
                "now and unmask the more recent version?",
                PM_NAME,
                style=wx.YES | wx.NO | wx.ICON_EXCLAMATION)
                # YES: "Uninstall (recommended)"
                # NO: "I will uninstall it later"
            if dlg.ShowModal() != wx.ID_YES:
                return
            # uninstall, update utils and reload if enabled
            self.uninstallPlugin(key)
            self.installPlugin(key)

    @eg.LogIt
    def fetchAvailablePlugins(self, reloadMode):
        """
        Fetch plugins from all enabled repositories.
        reloadMode = true:  Fully refresh data from all (enabled) repositories
        reloadMode = false: Fetch unready repositories only
        """

        if reloadMode:
            self.repositories.PopulateRepoList()
            self.plugins.clearRepoCache()
            self.plugins.ScanAllInstalledPlugins()

        for key in self.repositories.GetEnabledRepos():
            if reloadMode or self.repositories.GetAllRepos()[key]["state"] == REPO_STATE_REQ_FETCHING:  # if state = 3 (error or not fetched yet), try to fetch once again
                self.repositories.DoFetching(key)

        # if self.repositories.fetchingInProgress():
        #     fetchDlg = PluginInstallerFetchingDialog(iface.mainWindow())
        #     fetchDlg.exec_()
        #     del fetchDlg
        #     for key in self.repositories.GetAllRepos():
        #         self.repositories.killConnection(key)

        unavailable_repos = self.repositories.GetAllUnavailableRepos()
        if unavailable_repos and \
                unavailable_repos != self.repositories.GetEnabledRepos():
            for key in unavailable_repos:
                message = "Error reading repository:" + " " + key + \
                                "\n\n" + self.repositories.GetAllRepos()[key]["error"]
                dlg = wx.MessageBox(message, style = wx.OK | wx.CENTRE,
                                caption="EventGhost Plugin Installer")
                dlg.ShowModal()

        # finally, rebuild plugins from the caches
        self.plugins.rebuild()

    @eg.LogIt
    def exportRepositoriesToManager(self):
        """ Update manager's repository tree widget with current data """
        repositories = self.repositories
        lst = self.gui.lstRepo
        lst.DeleteAllItems()
        all_repos = repositories.GetAllRepos()
        for key in all_repos:
            url = all_repos[key]["url"] + repositories.GetUrlParameters()

            itemData = {
                "name": key,
                "url": url,
                "enabled": all_repos[key]["enabled"],
                "valid": all_repos[key]["valid"] and "true" or "false",
                "state": str(all_repos[key]["state"]),
                "error": all_repos[key].get("error",""),
            }
            item = lst.Append([itemData["state"], itemData["name"], itemData["url"]])
            lst.GetItem(item).SetPyData(itemData)
        #lst.SetColumnWidth(0, ULC.ULC_AUTOSIZE)
        lst.SetColumnWidth(1, ULC.ULC_AUTOSIZE)
        lst.SetColumnWidth(2, ULC.ULC_AUTOSIZE_FILL)

    @eg.LogIt
    def exportPluginsToManager(self):
        self.UpdatePluginListBox(self.plugins.all())

    @eg.LogItNoArgs
    def UpdatePluginListBox(self, plugins):
        self.gui.UpdateList(self.plugins.pluginsToShow(plugins.copy()))

    @eg.LogIt
    def reloadAndExportData(self):
        """ Reload All repositories and export data to the Plugin Manager """
        self.fetchAvailablePlugins(reloadMode=True)
        self.exportRepositoriesToManager()
        self.exportPluginsToManager()

    @eg.LogIt
    def onManagerClose(self):
        """ Call this method when closing manager window.
        It resets last-use-dependent values. """
        self.plugins.updateSeenPluginsList()
        Config.last_start = wx.DateTime().Today().FormatISODate()

    @eg.LogIt
    def upgradeAllUpgradeable(self):
        """ Reinstall all upgradeable plugins """
        for key in self.plugins.allUpgradeable():
            self.installPlugin(key)

    @eg.LogIt
    def installPlugin(self, guid):
        """ Install given plugin """
        pluginInfo = self.plugins.all()[guid]
        if not pluginInfo:
            return
        if pluginInfo.status == "newer" and not pluginInfo.error:
            # ask for confirmation if user downgrades an usable plugin
            rc = eg.MessageBox(
                "Are you sure you want to downgrade the "
                "plugin to the latest available version? "
                "The installed one is newer!",
                PM_NAME,
                parent=self.gui,
                style=wx.YES | wx.CANCEL | wx.ICON_EXCLAMATION
            )
            if rc != wx.ID_YES:
                return

        url = self.plugins.GetDownloadUrl(guid)
        downloadedFile = self.DownloadFile(url)
        try:
            eg.PluginInstall.Import(filepath=downloadedFile)
        except BadZipfile:
            with open(downloadedFile, "rt") as f:
                txt = f.read()
            if txt.upper().startswith("<!DOCTYPE HTML"):
                eg.HtmlMessageBox(
                    txt.decode("utf8"),
                    PM_NAME,
                    parent=self.gui,
                    style=wx.OK | wx.ICON_ERROR
                )
            else:
                eg.MessageBox(
                    "Downloaded file is corrupted! "
                    "The plugin will not be installed.\n"+repr(sys.exc_info()),
                    PM_NAME,
                    parent=self.gui,
                    style=wx.OK | wx.ICON_ERROR
                )
            return
        self.UpdateLists()
        eg.MessageBox(
            "Plugin '{0}' was successfully installed.\n"
            "Now you can add it to your configuration tree."
            .format(pluginInfo.name),
            PM_NAME,
            parent=self.gui,
            style=wx.OK | wx.ICON_INFORMATION
        )

    @eg.LogIt
    def uninstallPlugin(self, guid):
        """ Uninstall given plugin """
        actionItemCls = eg.document.ActionItem
        def SearchFunc(obj):
            if obj.__class__ == actionItemCls:
                if obj.executable and obj.executable.plugin.info.guid == guid:
                    return True
            return None

        inUse = eg.document.root.Traverse(SearchFunc) is not None
        if inUse:
            eg.MessageBox(parent=self.gui,
                message=eg.text.General.deletePlugin,
                caption=PM_NAME,
                style=wx.NO_DEFAULT | wx.OK | wx.ICON_EXCLAMATION,
            )
            return

        if guid in self.plugins.all():
            pluginInfo = self.plugins.all()[guid]
        else:
            pluginInfo = self.plugins.local_cache[guid]
        if not pluginInfo:
            return
        # TODO: check the following
        notAvailable = pluginInfo.status == "orphan" and not pluginInfo.error
        if notAvailable:
            rc = eg.MessageBox(
                "Warning: this plugin isn't available in any "
                "accessible repository!\n"
                "Are you sure you want to uninstall plugin\n"
                "'{p.name}' (version {p.version})?".
                format(p=pluginInfo),
                PM_NAME,
                parent=self.gui,
                style=wx.NO_DEFAULT | wx.YES | wx.NO | wx.ICON_WARNING
            )
            if rc != wx.ID_YES:
                return

        remove_plugin_dir(self.plugins.local_cache[guid].path)
        self.UpdateLists()
        eg.MessageBox(
            "Plugin '{0}' was removed successfully."
            .format(pluginInfo.name),
            PM_NAME,
            parent=self.gui,
            style=wx.OK | wx.ICON_INFORMATION
        )

    def UpdateLists(self):
        # update the list of plugins in plugin handling routines
        self.plugins.ScanAllInstalledPlugins()
        self.plugins.rebuild()
        self.exportPluginsToManager()
        self.DoViewChange(self.gui.lstView.GetSelection())

    def DownloadFile(self, url):
        tmpFile = tempfile.mktemp()
        # NOTE: stream=True
        r = requests.get(url, stream=True)

        # maxVal = int(r.headers['content-length'])
        # disabled progressdialog because plugins are small sized
        # dlg = wx.ProgressDialog(title="EventGhost Plugin Installer",
        #                         message="downloading plugin...",
        #                         maximum=maxVal,
        #                         style=wx.PD_SMOOTH |
        #                               wx.PD_AUTO_HIDE |
        #                               wx.PD_ELAPSED_TIME)
        # progress = 0

        with open(tmpFile, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                #progress += len(chunk)
                #dlg.Update(min(progress, maxVal))
                # else:
                #     print "none chunk"
        #dlg.Destroy()
        return tmpFile


    @eg.LogIt
    def InitGUI(self, mainFrame):
        gui = self.gui = PluginManagerGUI(mainFrame, title=PM_NAME)
        self.gui.chkUpdatecheck.SetValue(Config.check_on_show_PM)
        self.gui.chkExperimetal.SetValue(Config.allow_experimental)
        self.gui.chkDeprecated.SetValue(Config.allow_deprecated)
        intervall = UPDATE_CHECK_INTERVAL.index(Config.check_interval)
        self.gui.chcIntervall.SetSelection(intervall)

        gui.lstPlugins.Bind(wx.EVT_LISTBOX, self.OnPluginSelected)
        gui.lstView.Bind(wx.EVT_LISTBOX, self.OnViewChange)
        gui.Bind(wx.EVT_CLOSE, self.OnDlgClose)
        gui.Bind(wx.EVT_BUTTON, self.OnDlgOk, id=wx.ID_OK)
        gui.Bind(wx.EVT_BUTTON, self.OnDlgHelp, id=wx.ID_HELP)
        gui.btnInstall.Bind(wx.EVT_BUTTON, self.OnInstall)
        gui.btnUninstall.Bind(wx.EVT_BUTTON, self.OnUninstall)

    def OnUninstall(self, event):
        idx = self.gui.lstPlugins.GetSelection()
        itemData = self.gui.lstPlugins.GetClientData(idx)
        self.uninstallPlugin(itemData.guid)

    def OnInstall(self, event):
        idx = self.gui.lstPlugins.GetSelection()
        itemData = self.gui.lstPlugins.GetClientData(idx)
        self.installPlugin(itemData.guid)

    @eg.LogIt
    def OnPluginSelected(self, event):
        self.gui.showPluginDetails(event.ClientData)

    @eg.LogIt
    def OnDlgClose(self, event):
        self.onManagerClose()
        #self.gui.Destroy()
        self.gui.Hide()
        event.Skip()

    @eg.LogIt
    def OnDlgOk(self, event):
        interval = UPDATE_CHECK_INTERVAL[self.gui.chcIntervall.GetSelection()]
        Config.check_interval = interval
        Config.check_on_show_PM = self.gui.chkUpdatecheck.IsChecked()
        Config.allow_experimental = self.gui.chkExperimetal.IsChecked()
        Config.allow_deprecated = self.gui.chkDeprecated.IsChecked()
        self.onManagerClose()
        #self.gui.Destroy()
        self.gui.Hide()
        event.Skip()

    @eg.LogIt
    def OnDlgHelp(self, event):
        event.Skip()

    @eg.LogIt
    def OnViewChange(self, event):
        self.DoViewChange(event.Selection)

    def DoViewChange(self, viewType=0):
        info = tabInfoHTML + tabDescriptions[viewType]
        self.gui.htmlDescreption.SetPage(info, "")
        self.gui.btnInstall.Disable()
        self.gui.btnUninstall.Disable()
        funcLst = [self.plugins.all,
            self.plugins.allInstalled,
            self.plugins.allNotInstalled,
            self.plugins.allUpgradeable,
            self.plugins.allNew,
            self.plugins.allInvalid,
            ]
        func = funcLst[viewType]
        items = func()
        self.UpdatePluginListBox(items)


class ActionsMapping(object):
    def __init__(self, info):
        self.info = info
        self.actions = {}

    def __getitem__(self, name):
        if name in self.actions:
            return self.actions[name]

        class Action(eg.ActionBase):
            pass
        Action.__name__ = name
        action = self.info.actionGroup.AddAction(Action, hidden=True)
        self.actions[name] = action
        return action

    def __setitem__(self, name, value):
        self.actions[name] = value


class LoadErrorPlugin(eg.PluginBase):
    def __init__(self):
        raise self.Exceptions.PluginLoadError

    def __start__(self, *dummyArgs):
        raise self.Exceptions.PluginLoadError


class NonexistentPlugin(eg.PluginBase):
    class text:
        pass

    def __init__(self):
        raise self.Exceptions.PluginNotFound

    def __start__(self, *dummyArgs):
        raise self.Exceptions.PluginNotFound

    def GetLabel(self, *dummyArgs):
        return '<Unknown Plugin "%s">' % self.name


class NonexistentPluginInfo(eg.PluginInstanceInfo):
    def __init__(self, guid, name):
        self.guid = guid
        self.name = name
        self.pluginName = name

        class Plugin(NonexistentPlugin):
            pass

        Plugin.__name__ = name
        self.pluginCls = Plugin


class Repositories(object):
    """ A dict-like class for handling repositories data """

    def __init__(self, gui, plugins):
        self.gui = gui
        self.plugins = plugins
        self.repositories = {}
        self.httpId = {}   # {httpId : repoName}
        self.PopulateRepoList()
        self.gui.Bind(EVT_REPOSITORY_FETCHED, self.OnRepositoryFetched)

    @eg.LogIt
    def GetAllRepos(self):
        """ return dict of all repositories """
        return self.repositories

    @eg.LogIt
    def GetEnabledRepos(self):
        """ return dict of all enabled and valid repositories """
        repos = {}
        for key in self.repositories:
            if self.repositories[key]["enabled"] and \
                self.repositories[key]["valid"]:
                    repos[key] = self.repositories[key]
        return repos

    @eg.LogIt
    def GetAllUnavailableRepos(self):
        """ return dict of all unavailable repositories """
        repos = {}
        for i in self.repositories:
            if self.repositories[i]["enabled"] \
                and self.repositories[i]["valid"] \
                and self.repositories[i]["state"] == REPO_STATE_REQ_FETCHING:
                    repos[i] = self.repositories[i]
        return repos

    @eg.LogItWithReturn
    def GetUrlParameters(self):
        """ return GET parameters to be added to every request """
        return "?current={0}" .format(eg.Version.string)

    @eg.LogItWithReturn
    def GetUrl(self, repo):
        return self.repositories[repo]["url"]

    @eg.LogIt
    def setRepositoryData(self, reposName, key, value):
        """ write data to the repositories dict """
        self.repositories[reposName][key] = value

    @eg.LogIt
    def remove(self, reposName):
        """ remove given item from the repositories dict """
        del self.repositories[reposName]

    @eg.LogIt
    def rename(self, oldName, newName):
        """ rename repository key """
        if oldName == newName:
            return
        self.repositories[newName] = self.repositories[oldName]
        del self.repositories[oldName]

    @eg.LogItWithReturn
    def CheckingOnStartInterval(self):
        """
        Check if the interval value for update checking is one of the
        allowed values: 0,1,3,7,14,30 days
        1 is the default value, 0 means
        """
        interval = Config.check_interval
        if not isinstance(interval, int):
            if isinstance(interval, float):
                interval = int(round(interval))
            else:
                # fallback do 1 day by default
                interval = 1
        if interval < 0:
            interval = 1
        # allowed values:
        for j in [1, 3, 7, 14, 30]:
            if interval >= j:
                interval = j
        Config.check_interval = interval
        return interval

    @eg.LogItWithReturn
    def GetLastStartDay(self):
        # Settings may contain invalid value...
        day = wx.DateTime()
        try:
            ok = day.ParseISODate(Config.last_start)
        except TypeError:
            ok = False
        if ok:
            return day
        return wx.DateTime().Today()

    @eg.LogItWithReturn
    def IsTimeForChecking(self):
        """ determine whether it's the time for checking for news and updates now """
        if self.CheckingOnStartInterval() == 0:
            return True
        try:
            lastDate = self.GetLastStartDay()
            interval = (wx.DateTime_Today() - lastDate).days
        except (ValueError, AssertionError):
            interval = 1
        return interval >= self.CheckingOnStartInterval()

    @eg.LogIt
    def PopulateRepoList(self):
        """ populate the repositories dict"""
        self.repositories = {}
        for repo in Config.repositories:
            self.repositories[repo[0]] = {
                "url": repo[1],
                "enabled": repo[2],
                "valid": repo[3],
                "state": REPO_STATE_REQ_FETCHING,
                "verify": repo[4],
            }

        official_repo_present = False
        for key, items in self.repositories.iteritems():
            if items["url"] == OFFICIAL_REPO["url"]:
                official_repo_present = True
            elif items["url"] in OFFICIAL_REPO["deprecated"]:
                # correct a depreciated url
                self.repositories[key]["url"] = OFFICIAL_REPO["url"]
                official_repo_present = True

        if not official_repo_present:
            # official repository is not in the list of repositories -> add it.
            key = OFFICIAL_REPO["name"]
            repo =  {
                "url": OFFICIAL_REPO["url"],
                "enabled": True,
                "valid": True,
                "state": REPO_STATE_REQ_FETCHING,
                "verify": True,
            }
            self.repositories[key] = repo
            repos = []
            for name, repo in self.repositories.iteritems():
                repos.append([
                    name,
                    repo["url"],
                    repo["enabled"],
                    repo["valid"],
                ])
            Config.repositories = repos

    def FetchRepositories(self):
        all_enabled_repos = self.GetEnabledRepos()
        if Config.check_on_show_PM \
            and self.IsTimeForChecking() \
            and all_enabled_repos:
                self.RequestFetching(all_enabled_repos)
        else:
            # no fetching at start, so mark all enabled repositories
            # as requesting to be fetched.
            for key in all_enabled_repos:
                self.repositories[key]["state"] = REPO_STATE_REQ_FETCHING

    def RequestFetching(self, repos):
        # start fetching repositories
        dlg = wx.ProgressDialog(
            "fetching repositories", "fetching repositories...",
            maximum=100, style=wx.PD_SMOOTH
        )
        dlg.Pulse()
        dlg.Show()
        self.gui.Bind(
            EVT_CHECKING_DONE, lambda event: self.checkingDone(dlg=dlg)
        )
        for key in repos:
            self.DoFetching(key)

    @eg.LogIt
    def DoFetching(self, repo):
        """ start fetching the repository given by repo """
        self.repositories[repo]["state"] = REPO_STATE_LOADING
        # TODO: handle the params per repo (user editable)
        url = self.repositories[repo]["url"] + self.GetUrlParameters()
        try:
            self.repositories[repo]["request"] = requests.get(
                url,
                verify=self.repositories[repo]["verify"],
                timeout=10.0,
            )
        except requests.ConnectionError as err:
            self.repositories[repo]["error"] = "connection error"
            self.repositories[repo]["state"] = REPO_STATE_ERROR
            eg.MessageBox(
                "Couldn't connect to repository:\n{0}\n({1})".format(
                    repo, self.repositories[repo]["url"]
                ),
                PM_NAME, parent=self.gui, style=wx.OK | wx.ICON_ERROR
            )
            return

        self.repositories[repo]["xmlData"] = \
            self.repositories[repo]["request"].content
        self.xmlDownloaded(repo, url, self.repositories[repo]["xmlData"])

    @eg.LogIt
    def checkingDone(self, dlg):
        """ Remove the "Looking for new plugins..." label and
        display a notification instead if any updates or news available """
        dlg.Destroy()
        del dlg
        # LookForObsoletePlugins ??
        return
        if not self.statusLabel:
            # only proceed if the label is present
            return
        # rebuild plugins cache
        self.plugins.rebuild()

    def OnRepositoryFetched(self, event):
        pass
        # Update the status of the repo in the listview
        # self.repositiories[event.repo]

    @eg.LogItWithReturn
    def fetchingInProgress(self):
        """ return true if fetching repositories is still in progress """
        for key in self.repositories:
            if self.repositories[key]["state"] == REPO_STATE_LOADING:
                return True
        return False

    @eg.LogIt
    def killConnection(self, key):
        """ kill the fetching on demand """
        if self.repositories[key]["state"] == REPO_STATE_LOADING \
            and self.repositories[key]["xmlData"] \
            and self.repositories[key]["xmlData"].isRunning():
                self.repositories[key]["xmlData"].finished.disconnect()
                self.repositories[key]["xmlData"].abort()

    @eg.LogItNoArgs
    def xmlDownloaded(self, repo, url, xmlData):
        """ populate the plugins object with the fetched data """
        try:
            xd = xmltodict.parse(xmlData)
        except xml.parsers.expat.ExpatError as err:
            msg = "Error while parsing data from repository.\n({0})".format(
                err.message
            )
            self.repositories[repo]["error"] = msg
            self.repositories[repo]["state"] = REPO_STATE_ERROR
            eg.MessageBox(
                msg, PM_NAME, parent=self.gui, style=wx.OK | wx.ICON_ERROR
            )
            return

        try:
            rpl = xd["repository"]["plugins"]["egplugin"]
        except KeyError as err:
            msg = "Data from repository has wrong format.\n" \
                  "Missing Key: {0}".format(err)
            self.repositories[repo]["error"] = msg
            self.repositories[repo]["state"] = REPO_STATE_ERROR
            eg.MessageBox(
                msg, PM_NAME, parent=self.gui, style=wx.OK | wx.ICON_ERROR
            )
            return

        if not rpl:
            # no plugin metadata found
            return

        def MakeBool(value):
            try:
                return value.upper() in ["TRUE", "YES", "1"]
            except:
                return False

        for plgn in rpl:
            fileName = plgn.get("file_name")
            if not fileName:
                try:
                    fileName = plgn.get("downloadUrl").rsplit("/", 1)[1]
                except AttributeError:
                    pass

            egMinVersion = plgn.get("egMinVersion")
            egMinVersion = egMinVersion if egMinVersion is not None else "0.0.0"
            egMaxVersion = plgn.get("egMaxVersion")
            egMaxVersion = egMaxVersion if egMaxVersion is not None else "999.999.999"
            plugin_info = eg.PluginModuleInfo(plgn.get("downloadUrl"))
            try:
                plugin_info.RegisterPlugin(
                    name=plgn.get("name"),
                    description=plgn.get("description"),
                    kind=plgn.get("kind"),
                    author=plgn.get("author"),
                    icon=plgn.get("icon"),
                    url=plgn.get("url"),
                    guid=plgn.get("guid"),
                    hardwareId=plgn.get("hardwareId", ""),
                    longDescription=plgn.get("longDescription"),
                    experimental=MakeBool(plgn.get("experimental", False)),
                    deprecated=MakeBool(plgn.get("deprecated", False)),
                    issuesUrl=plgn.get("issuesUrl"),
                    codeUrl=plgn.get("codeUrl"),
                    pluginHelp=plgn.get("pluginHelp"),
                    egVersion=None,
                    egMinVersion=egMinVersion,
                    egMaxVersion=egMaxVersion,
                    changelog=plgn.get("changelog", ""),
                )
            except eg.Exceptions.RegisterPluginException:
                # PluginManager specific
                plugin_info.versionAvailable = plgn.get("version")
                plugin_info.downloadUrl = plgn.get("downloadUrl")
                plugin_info.filename = fileName
                plugin_info.available = True
                plugin_info.status = "not installed"
                plugin_info.error = ""
                plugin_info.error_details = ""
                plugin_info.zipRepository = repo
                plugin_info.library = url.rpartition("/")[0]
                plugin_info.valid = True
            self.plugins.addFromRepository(plugin_info)

        self.repositories[repo]["state"] = REPO_STATE_LOADED_OK
        wx.PostEvent(self.gui, RepositoryFetched(repo=repo))
        # is the checking done?
        if not self.fetchingInProgress():
            wx.PostEvent(self.gui, CheckingDone())


class PluginCache(object):
    """ A dict-like class for handling plugins data """

    def __init__(self):
        self.plugin_cache = {}  # list of plugins
        self.local_cache = {}  # list of local installed plugins
        self.repo_cache = {}  # list of repositories
        self.obsolete_plugins = []  # list of outdated 'user' plugins masking newer 'core' ones
        self.metadata = {}
        self._update_seen = False
        self.ScanAllInstalledPlugins()

    @eg.LogIt
    def GetPluginInfo(self, guid):
        if guid in self.local_cache:
            return self.local_cache[guid]
        else:
            for guid, info in self.local_cache.iteritems():
                if info.pluginName == guid:
                    return info
        return None

    @eg.LogIt
    def GetPluginInfoList(self, rescan=False):
        """
        Get a list of all PluginInfo for all plugins in the plugin directory
        """
        if rescan:
            self.ScanAllInstalledPlugins()
        infoList = self.local_cache.values()
        infoList.sort(key=lambda pluginInfo: pluginInfo.name.lower())
        return infoList

    @eg.LogItNoArgsWithReturn
    def pluginsToShow(self, plugin_list):
        plugins = []
        for guid, plug in plugin_list.iteritems():
            if plug.experimental == True and \
                not Config.allow_experimental or \
                plug.deprecated == True and \
                not Config.allow_deprecated:
                    continue
            plugins.append([plug.name, plug])
        return plugins

    @eg.LogIt
    def all(self):
        """ return all plugins """
        return self.plugin_cache

    @eg.LogIt
    def allInstalled(self):
        """ return all installed plugins """
        return {
            guid: self.plugin_cache[guid] for guid in self.local_cache
            }

    @eg.LogIt
    def allNotInstalled(self):
        """ return all plugins that are not installed """
        return {
            guid: self.plugin_cache[guid] for guid in self.plugin_cache if
                guid not in self.local_cache
            }

    @eg.LogIt
    def allUpgradeable(self):
        """ return all upgradeable plugins """
        return {key: self.plugin_cache[key] for key in self.plugin_cache if
                self.plugin_cache[key].status == "upgradeable"}

    @eg.LogIt
    def allNew(self):
        """ return all new plugins """
        self._update_seen = True
        return {guid: self.plugin_cache[guid] for guid in self.plugin_cache if
                self.plugin_cache[guid].status == "new"}

    @eg.LogIt
    def allInvalid(self):
        """ return all invalid plugins """
        plugins = {guid: self.plugin_cache[guid] for guid in self.plugin_cache if
                (self.plugin_cache[guid].status in ["orphan", "broken"]
                 or self.plugin_cache[guid].deprecated)
                }
        return plugins

    @eg.LogItWithReturn
    def keyByUrl(self, name):
        """ return plugin key by given url """
        plugins = [i for i in self.plugin_cache if self.plugin_cache[i].download_url == name]
        if plugins:
            return plugins[0]
        return None

    @eg.LogIt
    def clearRepoCache(self):
        """ clears the repo cache before re-fetching repositories """
        self.repo_cache = {}

    @eg.LogItNoArgs
    def addFromRepository(self, plugin):
        """ add given plugin to the repo_cache """
        repo = plugin.zipRepository
        try:
            self.repo_cache[repo] += [plugin]
        except KeyError:
            self.repo_cache[repo] = [plugin]

    @eg.LogIt
    def removeInstalledPlugin(self, key):
        """ remove given plugin from the local_cache """
        if key in self.local_cache:
            del self.local_cache[key]

    @eg.LogIt
    def removeRepository(self, repo):
        """ remove whole repository from the repo_cache """
        if repo in self.repo_cache:
            del self.repo_cache[repo]

    @eg.TimeIt
    def ScanAllInstalledPlugins(self):
        """
        Scans the plugin directories to get all needed information for all
        installed plugins.
        """
        self.local_cache.clear()

        # scan through all directories in all plugin directories
        for root in eg.pluginDirs:
            for dirname in os.listdir(root):
                # filter out non-plugin names
                if dirname.startswith(".") or dirname.startswith("_"):
                    continue
                pluginDir = join(root, dirname)
                if not isdir(pluginDir):
                    continue
                if not exists(join(pluginDir, "__init__.py")):
                    continue
                info = eg.PluginModuleInfo(pluginDir)
                info.library = pluginDir
                self.local_cache[info.guid] = info

    @eg.LogIt
    def rebuild(self):
        """ build or rebuild the plugin_cache from the caches """
        self.plugin_cache = {}
        for guid in self.local_cache:
            self.plugin_cache[guid] = copy(self.local_cache[guid])
        for repo in self.repo_cache.values():
            for repo_plugin in repo:
                plugin = copy(repo_plugin)  # do not update repo_cache elements!
                guid = plugin.guid
                # check if the plugin is allowed and if there isn't any better one added already.

                already_in_plugin_cache = guid in self.plugin_cache
                version_vailable = parse_version(plugin.versionAvailable)

                newer_version_available = False
                if already_in_plugin_cache:
                    ver_in_cache = parse_version(
                        self.plugin_cache[guid].version
                    )
                    newer_version_available = version_vailable > ver_in_cache

                chk3 = (already_in_plugin_cache and newer_version_available)
                chk2 = (Config.allow_deprecated and plugin.deprecated)
                chk1 = (Config.allow_experimental and plugin.experimental)
                chk4 = (not chk2 and not chk1 and not newer_version_available)
                chk5 = (not already_in_plugin_cache and chk1 and chk2)
                if chk5:
                    continue
                if True:  # chk1 or chk2 or chk3:
                    # Add the available one if not present yet or
                    # update it if present already.
                    if not already_in_plugin_cache:
                        # just add a new plugin
                        self.plugin_cache[guid] = plugin
                    else:
                        # update local plugin with remote metadata
                        # description, about, icon: only use remote data if local one not available. Prefer local version because of i18n.
                        # NOTE: don't prefer local name to not desynchronize names if repository doesn't support i18n.
                        # Also prefer local icon to avoid downloading.
                        for attrib in TRANSLATABLE_ATTRIBUTES + ["icon"]:
                            if attrib != "name":
                                if not getattr(self.plugin_cache[guid], attrib)\
                                    and getattr(plugin, attrib):
                                        setattr(
                                            self.plugin_cache[guid],
                                            attrib,
                                            getattr(plugin, attrib)
                                        )
                        # other remote metadata is prefered:
                        for attrib in [
                            "name", "description", "pluginHelp", "kind",
                            "deprecated", "changelog", "author", "url",
                            "issuesUrl", "codeUrl", "experimental",
                            "versionAvailable", "zipRepository",
                            "downloadUrl", "filename"]:
                            if attrib not in TRANSLATABLE_ATTRIBUTES \
                                or attrib == "name":  # include name!
                                if getattr(plugin, attrib):
                                    setattr(
                                        self.plugin_cache[guid],
                                        attrib,
                                        getattr(plugin, attrib)
                                    )
                    # set status
                    #
                    # installed   available   status
                    # ---------------------------------------
                    # none        any         "not installed" (will be later checked if is "new")
                    # any         none        "orphan"
                    # same        same        "installed"
                    # less        greater     "upgradeable"
                    # greater     less        "newer"
                    if not plugin.versionAvailable:
                        self.plugin_cache[guid].status = "orphan"
                    elif not guid in self.local_cache:
                        self.plugin_cache[guid].status = "not installed"
                    elif newer_version_available:
                        self.plugin_cache[guid].status = "upgradeable"
                    elif guid in self.local_cache:
                        self.plugin_cache[guid].status = "installed"
                    elif ver_in_cache > version_vailable:
                        self.plugin_cache[guid].status = "newer"
                    else:
                        self.plugin_cache[guid].status = "unknown"

                    # debug: test if the status match the "installed" tag:
                    pt1 = (self.plugin_cache[guid].status in ["not installed"])
                    if pt1 and guid in self.local_cache:
                        raise Exception("Error: plugin status is ambiguous (1)")
                    pt1 = (self.plugin_cache[guid].status in ["installed", "orphan", "upgradeable", "newer"])
                    if pt1 and not guid in self.local_cache:
                        inf = "-----------------------------------------------"
                        inf += '\nplugin: ' + self.plugin_cache[guid]["name"] + " (" + guid + ")"
                        inf += '\nself.plugin_cache[key].status = ' + repr(self.plugin_cache[guid].status)
                        inf += '\nself.plugin_cache[key].versionAvailable = ' + repr(self.plugin_cache[guid].installed)

                        #raise Exception("Error: plugin status is ambiguous (2)" + inf)
                        print("Error: plugin status is ambiguous (2)" + inf)
        self.markNews()

    @eg.LogIt
    def markNews(self):
        """ mark all new plugins as new """
        for guid in self.plugin_cache:
            if guid not in Config.seen_plugins and \
                    self.plugin_cache[guid].status == "not installed":
                self.plugin_cache[guid].status = "new"

    @eg.LogIt
    def updateSeenPluginsList(self):
        """ update the list of all seen plugins """
        if self._update_seen:
            # TODO: only mark all as seen, if user was on page "new plugins"
            Config.seen_plugins = self.plugin_cache.keys()

    @eg.LogItWithReturn
    def isThereAnythingNew(self):
        """ return true if an upgradeable or new plugin detected """
        for plugin in self.plugin_cache.values():
            if plugin.status in ["upgradeable", "new"]:
                return True
        return False

    def GetDownloadUrl(self, guid):
        if self.plugin_cache[guid].downloadUrl:
            return self.plugin_cache[guid].downloadUrl

        repoUrl = eg.pluginManager.repositories.GetUrl(
            self.plugin_cache[guid].zipRepository
        )
        url = repoUrl.rpartition("/")[0] + "/"
        url += self.plugin_cache[guid].name + "_"
        url += self.plugin_cache[guid].versionAvailable.replace(".", "_")
        url += ".egplugin"


class PanelViewSelection(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelViewSelection, self).__init__(*args, **kwargs)

        # if adding/removing items here, be aware to adapt the values
        # in EGPluginInstaller.OnOk()
        choices = ["All plugins", "Installed plugins", "Not installed plugins",
                   "Upgradeable plugins", "New plugins", "Invalid plugins"]
        lstView = wx.ListBox(self, ID_VIEW, choices=choices)
        szr = wx.BoxSizer()
        szr.Add(lstView, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(szr)
        self.Layout()


class PanelPluginList(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelPluginList, self).__init__(*args, **kwargs)

        lstPlugins = wx.ListBox(self, ID_PLUGIN_LIST)
        srchLabel = wx.StaticText(self, wx.ID_ANY, "Search")
        searchTxt = wx.TextCtrl(self, ID_PLUGIN_FILTER)

        szrSearch = wx.BoxSizer(wx.HORIZONTAL)
        szrSearch.Add(srchLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        szrSearch.Add(searchTxt, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(lstPlugins, 1, wx.ALL | wx.EXPAND, 5)
        szr.Add(szrSearch, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(szr)
        self.Layout()


class PanelDetailsAndAction(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelDetailsAndAction, self).__init__(*args, **kwargs)

        #self.htmlDescreption = wx.html.HtmlWindow(self, wx.ID_ANY)
        htmlDescreption = wx.html2.WebView.New(self, ID_PLUGIN_DETAILS)
        htmlDescreption.SetPage(tabInfoHTML + tabDescriptions[0], "")
        btnUpgradeAll = wx.Button(self, ID_UPGRADE_ALL, "Updgrade all")
        btnUninstall = wx.Button(self, ID_UNINSTALL, "Uninstall plugin")
        btnInstall = wx.Button(self, ID_INSTALL, "Install plugin")

        btnUpgradeAll.Disable()
        btnUninstall.Disable()
        btnInstall.Disable()

        szrBtns= wx.BoxSizer(wx.HORIZONTAL)
        szrBtns.Add(btnUpgradeAll, 0, wx.ALL, 5)
        szrBtns.AddSpacer((0, 0), 1, wx.EXPAND, 5)
        szrBtns.Add(btnUninstall, 0, wx.ALL, 5)
        szrBtns.Add(btnInstall, 0, wx.ALL, 5)

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(htmlDescreption, 1, wx.ALL | wx.EXPAND, 5)
        szr.Add(szrBtns, 0, wx.EXPAND, 5)
        self.SetSizer(szr)
        self.Layout()


def StaticCheckBox(parent, chkId, label, message, *args, **kwargs):
    sb = wx.StaticBox(parent)
    chkbox = wx.CheckBox(sb, chkId, label)
    infoText = IB.AutoWrapStaticText(sb, message)
    infoText.SetSizeHints(-1, 50)

    szr = wx.StaticBoxSizer(sb, wx.VERTICAL)
    szr.Add(chkbox, 0, wx.ALL, 5)
    szr.Add(infoText, 0, wx.ALL | wx.EXPAND, 5)
    return szr


def BoxUpdateIntervall(parent):
    msg = "NOTE: If this function is enabled, {0} will inform" \
          " you on startup whenever a new plugin or plugin update is " \
          "available. Otherwise, fetching repositories will be " \
          "performed during opening of the {1} window.".format(
              eg.APP_NAME, PM_NAME
          )

    sb = wx.StaticBox(parent)
    chk = wx.CheckBox(sb, ID_UPDATE_CHECK, "Check for plugin updates on startup")
    chc = wx.Choice(sb, ID_INTERVALL, choices=UPDATE_CHECK_CHOICES)
    chc.SetSelection(0)
    infoText = IB.AutoWrapStaticText(sb, msg)
    infoText.SetSizeHints(-1, 50)

    szrH = wx.BoxSizer(wx.HORIZONTAL)
    szrH.Add(chk, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
    szrH.Add(chc, 0, wx.ALL, 5)

    szr = wx.StaticBoxSizer(sb, wx.VERTICAL)
    szr.Add(szrH, 0, wx.ALL, 5)
    szr.Add(infoText, 0, wx.ALL | wx.EXPAND, 5)
    return szr


def BoxRepositories(parent):
    sb = wx.StaticBox(parent)
    lstRepo = ULC.UltimateListCtrl(sb, ID_REPO_LIST, agwStyle=wx.LC_REPORT)
    lstRepo.InsertColumn(0, "Status")
    lstRepo.InsertColumn(1, "Name")
    lstRepo.InsertColumn(2, "URL")
    btnRepload = wx.Button(sb, ID_REPO_RELOAD, "Reload repository")
    btnAdd = wx.Button(sb, ID_REPO_ADD, "Add")
    btnEdit = wx.Button(sb, ID_REPO_EDIT, "Edit...", )
    btnDelete = wx.Button(sb, ID_REPO_DELETE, "Delete")

    szrBtn = wx.BoxSizer(wx.HORIZONTAL)
    szrBtn.Add(btnRepload, 0, wx.ALL, 5)
    szrBtn.AddSpacer((0, 0), 1, wx.EXPAND, 5)
    szrBtn.Add(btnAdd, 0, wx.ALL, 5)
    szrBtn.Add(btnEdit, 0, wx.ALL, 5)
    szrBtn.Add(btnDelete, 0, wx.ALL, 5)

    szr = wx.StaticBoxSizer(sb, wx.VERTICAL)
    szr.Add(lstRepo, 1, wx.ALL | wx.EXPAND, 5)
    szr.Add(szrBtn, 0, wx.EXPAND, 5)
    return szr


class PanelSettings(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelSettings, self).__init__(*args, **kwargs)

        sbIntervall = BoxUpdateIntervall(self)
        msg = "NOTE: Experimental plugins are generally unsuitable for " \
              "production use. These plugins are in early stages of " \
              "development, and should be considered 'incomplete' or " \
              "'proof of concept' tools. The EventGhost Project does not " \
              "recommend installing these plugins unless you intend to " \
              "use them for testing purposes."

        sbExperimental = StaticCheckBox(self, message=msg, chkId=ID_EXPERIMENTAL,
                                        label="Show also experimental plugins")

        msg = "NOTE: Deprecated plugins are generally unsuitable for " \
              "production use. These plugins are unmaintained, and should " \
              "be considered 'obsolete' tools. The EventGhost Project does " \
              "not recommend installing these plugins unless you still need " \
              "it and there are no other alternatives available."
        sbDeprecated = StaticCheckBox(self, message=msg, chkId=ID_DEPRECATED,
                                      label="Show also deprecated plugins")

        sbRepositories = BoxRepositories(self)
        #sbRepositories.GetStaticBox().Hide()

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(sbIntervall, 0, wx.ALL | wx.EXPAND, 5)
        szr.Add(sbExperimental, 0, wx.ALL | wx.EXPAND, 5)
        szr.Add(sbDeprecated, 0, wx.ALL | wx.EXPAND, 5)
        szr.Add(sbRepositories, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(szr)
        self.Layout()


class PluginManagerGUI(wx.Frame):
    def __init__(self, *args, **kwargs):
        #kwargs.update({"style": wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER})
        super(PluginManagerGUI, self).__init__(*args, **kwargs)

        self._sortmode = LB_SORT_ASCENDING | LB_SORT_BY_NAME
        self._plugins = None

        mainBook = wx.Notebook(self, wx.ID_ANY)
        self.pagePlugins = MultiSplitterWindow(mainBook, style=wx.SP_LIVE_UPDATE)
        pageSettings = PanelSettings(mainBook)

        pnlView = PanelViewSelection(self.pagePlugins)
        pnlPluginlist = PanelPluginList(self.pagePlugins)
        pnlDetailsAndAction = PanelDetailsAndAction(self.pagePlugins)
        self.pagePlugins.AppendWindow(pnlView, 150)
        self.pagePlugins.AppendWindow(pnlPluginlist, 180)
        self.pagePlugins.AppendWindow(pnlDetailsAndAction)

        mainBook.AddPage(self.pagePlugins, "Plugins", True)
        mainBook.AddPage(pageSettings, "Settings", False)

        stLine = wx.StaticLine(self, wx.ID_ANY, style=wx.LI_HORIZONTAL)
        btnDlgOk = wx.Button(self, wx.ID_OK)
        btnDlgHelp = wx.Button(self, wx.ID_HELP)

        szrDlgBtn = wx.StdDialogButtonSizer()
        szrDlgBtn.AddButton(btnDlgOk)
        szrDlgBtn.AddButton(btnDlgHelp)
        szrDlgBtn.Realize()

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(mainBook, 1, wx.EXPAND | wx.ALL, 5)
        szr.Add(stLine, 0, wx.EXPAND | wx.ALL, 5)
        szr.Add(szrDlgBtn, 0, wx.ALL | wx.EXPAND, 15)

        self.SetSizer(szr)
        self.SetSize((900, 680))
        self.Layout()

        self.lstRepo = self.FindWindowById(ID_REPO_LIST)
        self.lstPlugins = self.FindWindowById(ID_PLUGIN_LIST)
        self.lstView = self.FindWindowById(ID_VIEW)
        self.htmlDescreption = self.FindWindowById(ID_PLUGIN_DETAILS)
        self.btnInstall = self.FindWindowById(ID_INSTALL)
        self.btnUninstall = self.FindWindowById(ID_UNINSTALL)
        self.btnUpgradeAll = self.FindWindowById(ID_UPGRADE_ALL)
        self.chkUpdatecheck = self.FindWindowById(ID_UPDATE_CHECK)
        self.chkExperimetal = self.FindWindowById(ID_EXPERIMENTAL)
        self.chkDeprecated = self.FindWindowById(ID_DEPRECATED)
        self.chcIntervall = self.FindWindowById(ID_INTERVALL)

        self.lstPlugins.Bind(wx.EVT_RIGHT_UP, self.OnListRightClick)

    def OnListRightClick(self, event):
        mnu = wx.Menu()
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_ASCENDING | LB_SORT_BY_NAME), "sort by name (ascending)")
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_DESCENDING | LB_SORT_BY_NAME), "sort by name (descending)")
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_ASCENDING | LB_SORT_BY_STATUS), "sort by status (ascending)")
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_DESCENDING | LB_SORT_BY_STATUS), "sort by status (descending)")
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_ASCENDING | LB_SORT_BY_VOTE), "sort by vote (ascending)")
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_DESCENDING | LB_SORT_BY_VOTE), "sort by vote (descending)")
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_ASCENDING | LB_SORT_BY_DOWNLOADS), "sort by downloads (ascending)")
        mnu.Append(wx.ID_HIGHEST + 1000 + (LB_SORT_DESCENDING | LB_SORT_BY_DOWNLOADS), "sort by downloads (descending)")

        #self.Bind(wx.EVT_MENU, lambda event: self.OnPaste(rcRow, rcCol, text), mn)
        mnu.Bind(wx.EVT_MENU, self.OnListPopupMenu)
        self.PopupMenu(mnu)
        mnu.Destroy()

    def OnListPopupMenu(self, event):
        sortmode = event.GetId() - wx.ID_HIGHEST - 1000
        self.SortList(sortmode)

    def SortList(self, sortmode):
        self._sortmode = sortmode
        if sortmode & LB_SORT_BY_NAME:
            self.SortByName()
        elif sortmode & LB_SORT_BY_STATUS:
            self.SortByStatus()
        elif sortmode & LB_SORT_BY_RELEASE_DATE:
            self.SortByReleaseDate()
        else:
            self._sortmode = LB_SORT_BY_NAME | LB_SORT_ASCENDING
            self.SortByName()
        if self._sortmode & LB_SORT_DESCENDING:
            self._plugins.reverse()
        self.RefreshList()

    def SortByName(self):
        self._plugins.sort(cmp=lambda x,y: cmp(x[0], y[0]))

    def SortByStatus(self):
        self._plugins.sort(cmp=lambda x, y:
                                cmp(x[1].status, y[1].status))

    def SortByReleaseDate(self):
        pass

    def RefreshList(self):
        lstPlugins = self.lstPlugins
        lstPlugins.Freeze()
        lstPlugins.Clear()
        for name, itemData in self._plugins:
            lstPlugins.Append(name, itemData)
        lstPlugins.Thaw()

    def UpdateList(self, lst, sortby=None):
        # type: (list, int) -> None
        '''
        :param lst: list [plugin name, metaData]
        :param sortby: optional sort flags
        :returns:
        '''
        self._plugins = lst
        self.SortList(sortby or self._sortmode)

    eg.LogItNoArgs
    def showPluginDetails(self, metadata):
        if not metadata:
            return
        html = "<style> body, table { padding:0px; margin:0px;" \
               "font-family:verdana; font-size: 12px; } div#votes {" \
               "width:360px; margin-left:98px; padding-top:3px; } </style>"

        # First prepare message box(es)
        if metadata.error:
            if metadata.error == "incompatible":
                errorMsg = "<b>{0}</b><br/>{1}".format(
                    "This plugin is incompatible with this version of EventGhost",
                    "Plugin is designed for EventGhost {0}".format(metadata.error_details))
            elif metadata.error == "dependent":
                errorMsg = "<b>{0}:</b><br/>{1}".format(
                    "This plugin requires a missing module",
                    metadata.error_details)
            else:
                errorMsg = "<b>{0}</b><br/>{1}".format(
                    "This plugin is broken",
                    metadata.error_details)
                html += '<table bgcolor="#FFFF88" cellspacing="2" ' \
                    'cellpadding="6" width="100%">' \
                    '<tr><td width="100%" style="color:#CC0000">' \
                    '{0}</td></tr></table>'.format(errorMsg)

        if metadata.status == "upgradeable":
            html += '<table bgcolor="#FFFFAA" cellspacing="2" ' \
                    'cellpadding="6" width="100%">' \
                    '<tr><td width="100%" style="color:#880000">' \
                    '<b>{0}</b></td></tr></table>'.format("There is a new version available")
        if metadata.status == "new":
            html += '<table bgcolor="#CCFFCC" cellspacing="2" ' \
                    'cellpadding="6" width="100%">' \
                     '<tr><td width="100%" style="color:#008800">' \
                     '<b>{0}</b></td></tr></table>'.format("This is a new plugin")
        if metadata.status == "newer":
            html += '<table bgcolor="#FFFFCC" cellspacing="2" ' \
                    'cellpadding="6" width="100%">' \
                     '<tr><td width="100%" style="color:#550000; vertical-align:middle">' \
                    '<b>{0}</b></td></tr></table>'.format(
                    "Installed version of this plugin is higher than"
                    " any version found in repository")
        if metadata.experimental:
            icn = os.path.join(eg.imagesDir, "pluginExperimental.png")
            html += '<table bgcolor="#EEEEBB" cellspacing="2" ' \
                    'cellpadding="2" width="100%">' \
                    '<tr><td><img src="file://{1}" width="32"></td>' \
                    '<td width="100%" style="color:#660000; vertical-align:' \
                    'middle"><b>{0}</b></td></tr></table>'.format(
                    "This plugin is experimental", icn)
        if metadata.deprecated:
            icn = os.path.join(eg.imagesDir, "pluginDeprecated.png")
            html += '<table bgcolor="#EEBBCC" cellspacing="2" ' \
                    'cellpadding="2" width="100%">' \
                    '<tr><td><img src="file://{1}" width="32"></td>' \
                    '<td width="100%" style="color:#660000; vertical-align: ' \
                    'middle"><b>{0}</b></td></tr></table>'.format(
                    "This plugin is deprecated", icn)

        # Now the metadata
        html += '<table cellspacing="4" width="100%"><tr><td ' \
                'valign="middle"><h1>&nbsp;'
        path = metadata.library
        icon = metadata.icon
        if icon is None:
            icon = eg.Icons.PLUGIN_ICON.key
        elif isinstance(icon, (eg.Icons.PathIcon, eg.Icons.StringIcon)):
            icon = icon.key
        if os.path.exists(icon) and os.path.isfile(icon):
            iconPath = "file://{0}".format(icon.replace('\\', '/'))
            html += '<img src="{0}">&nbsp;'.format(iconPath)
        else:
            src = '<img src="data:image/gif;base64,\n' + icon
            html += src + '">&nbsp;'

        html += "{0}</h1>".format(metadata.name)
        try:
            html += "<h5>{0}</h5>".format(metadata.description)
        except UnicodeEncodeError:
            html += "<h5>{0}</h5>".format(repr(metadata.description))

        if metadata.longDescription:
            about = metadata.longDescription
            html += about#.replace('\n', "<br/>")

        html += "<br/><br/>"
        if metadata.kind:
            html += "{0}: {1} <br/>".format("Kind", metadata.kind)
        # if metadata["tags"]:
        #     html += "{0}: {1} <br/>".format("Tags", metadata["tags"])
        if metadata.url or metadata.issuesUrl or metadata.codeUrl:
            html += "{0}: ".format("More info")
            if metadata.url:
                html += "<a href='{0}'>{1}</a> &nbsp; ".format(
                    metadata.url, "url")
            if metadata.issuesUrl:
                html += "<a href='{0}'>{1}</a> &nbsp; ".format(
                    metadata.issuesUrl, "issue tracker")
            if metadata.codeUrl:
                html += "<a href='{0}'>{1}</a>".format(
                    metadata.codeUrl, "source code")
            html += "<br/>"
        html += "<br/>"

        # if metadata.author.:
        #     html += "{0}: <a href='mailto:{1}'>{2}</a>".format(
        #         "Author", metadata.author_email, metadata.author_name)
        #     html += "<br/><br/>"
        if metadata.author:
            html += "{0}: {1}".format("Author", metadata.author)
            html += "<br/><br/>"

        if metadata.version:
            if metadata.version:
                ver = metadata.version
                if ver == "-1":
                    ver = '?'
                html += "Installed version: {0} (in {1})<br/>".format(
                    ver, path)
        if metadata.versionAvailable:
            html += "Available version: {0} (in {1})<br/>".format(
                metadata.versionAvailable, metadata.zipRepository)
        if metadata.changelog:
            html += "<br/>"
            changelog = "changelog:<br/>{0} <br/>".format(metadata.changelog)
            html += changelog.replace('\n', "<br/>")

        html += "</td></tr></table>"
        html += "</body>"

        self.htmlDescreption.SetPage(html, "")

        #  Set buttonInstall text (and sometimes focus)
        if metadata.status == "upgradeable":
            self.btnInstall.SetLabel("Upgrade Plugin")
        elif metadata.status == "newer":
            self.btnInstall.SetLabel("Downgrade Plugin")
        elif metadata.status == "not installed" or \
                metadata.status == "new":
            self.btnInstall.SetLabel("Install Plugin")
        else:
            # Default (will be grayed out if not available for reinstallation)
            self.btnInstall.SetLabel("Reinstall Plugin")

        # Enable/disable buttons
        core = metadata.kind == "core"
        self.btnInstall.Enable(
            (
                metadata.status != "orphan" or
                (
                    metadata.status != "not installed" and
                    metadata.status != "new"
                )
            ) and
            not core
        )
        self.btnUninstall.Enable(
            metadata.status in ["newer", "upgradeable", "installed"]  # "orphan"
        )
        # hide = not ((metadata.status == "not installed") or
        #         (metadata.status == "new") and not core)
        # self.btnUninstall.Show(hide)
