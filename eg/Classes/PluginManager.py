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
import wx.lib.newevent
import wx.richtext
import xmltodict
from pkg_resources import parse_version

import eg
from .PluginManagerSettings import Config, PLUGIN_DETAILS_HTML_STYLE, PM_NAME

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


@eg.AssertInMainThread
class PluginManager:
    """
    The main class for managing the plugin installer stuff.
    """
    def __init__(self):
        self.plugins = PluginCache()

    def GetPluginInfoList(self):
        return self.plugins.GetPluginInfoList()

    def GetPluginInfo(self, guid):
        return self.plugins.GetPluginInfo(guid)

    def OpenPlugin(self, guid, evalName, args, treeItem=None):
        moduleInfo = self.plugins.GetPluginInfo(guid)
        if moduleInfo is None:
            # we don't have such plugin
            clsInfo = NonexistentPluginInfo(guid, evalName)
        else:
            try:
                clsInfo = eg.PluginInstanceInfo.FromModuleInfo(moduleInfo)
            except eg.Exceptions.PluginLoadError:
                if evalName:
                    clsInfo = NonexistentPluginInfo(guid, evalName)
                else:
                    raise
        info = clsInfo.CreateInstance(args, evalName, treeItem)
        if moduleInfo is None:
            info.actions = ActionsMapping(info)
        return info

    def ShowPluginManager(self, mainFrame=None):
        self.repositories = Repositories(self.plugins)
        self.repositories.FetchRepositories()
        self.LookForObsoletePlugins()
        self.fetchAvailablePlugins(reloadMode=False)
        eg.pluginManagerDialog.UpdateRepositoriesList(self.repositories)
        eg.pluginManagerDialog.UpdatePluginList()
        eg.pluginManagerDialog.Show()
        Config.last_start = wx.DateTime().Today().FormatISODate()


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
    def OnPluginSelected(self, event):
        # guid = event.ClientData
        # if not guid:
        guid = event.GetData()

        html = PLUGIN_DETAILS_HTML_STYLE
        plugin_info = self.plugins.plugin_cache[guid]
        if not plugin_info:
            html += "<h3><i>No details available</i></h3>"
            eg.pluginManagerDialog.ShowPluginDetails(html)
            eg.pluginManagerDialog.EnableButton("PM_btn_Install", False)
            eg.pluginManagerDialog.EnableButton("PM_btn_Uninstall", False)
            return

        # html = "<style> body, table { padding:0px; margin:0px;" \
        #        "font-family:verdana; font-size: 12px; } div#votes {" \
        #        "width:360px; margin-left:98px; padding-top:3px; } </style>"

        # First prepare message box(es)
        if plugin_info.error:
            if plugin_info.error == "incompatible":
                error_msg = "<b>{0}</b><br/>{1}".format(
                    "This plugin is incompatible with this version "
                    "of {0}".format(eg.APP_NAME),
                    "Plugin is designed for "
                    "{0} {1}".format(eg.APP_NAME, plugin_info.error_details))
            elif plugin_info.error == "dependent":
                error_msg = "<b>{0}:</b><br/>{1}".format(
                    "This plugin requires a missing module",
                    plugin_info.error_details)
            else:
                error_msg = "<b>{0}</b><br/>{1}".format(
                    "This plugin is broken",
                    plugin_info.error_details)
            html += '<table bgcolor="#FFFF88" cellspacing="2" ' \
                'cellpadding="6" width="100%">' \
                '<tr><td width="100%" style="color:#CC0000">' \
                '{0}</td></tr></table>'.format(error_msg)

        if plugin_info.status == "upgradeable":
            html += '<table bgcolor="#FFFFAA" cellspacing="2" ' \
                    'cellpadding="6" width="100%">' \
                    '<tr><td width="100%" style="color:#880000">' \
                    '<b>{0}</b></td></tr>' \
                    '</table>'.format("There is a new version available")
        if plugin_info.status == "new":
            html += '<table bgcolor="#CCFFCC" cellspacing="2" ' \
                    'cellpadding="6" width="100%">' \
                     '<tr><td width="100%" style="color:#008800">' \
                     '<b>{0}</b></td></tr>' \
                    '</table>'.format("This is a new plugin")
        if plugin_info.status == "newer":
            html += '<table bgcolor="#FFFFCC" cellspacing="2" ' \
                    'cellpadding="6" width="100%">' \
                     '<tr><td width="100%" style="color:#550000; ' \
                    'vertical-align:middle">' \
                    '<b>{0}</b></td></tr></table>'.format(
                    "Installed version of this plugin is higher than"
                    " any version found in repository")

        if plugin_info.experimental:
            icn = os.path.join(eg.imagesDir, "pluginExperimental.png")
            html += '<table bgcolor="#EEEEBB" cellspacing="2" ' \
                    'cellpadding="2" width="100%">' \
                    '<tr><td><img src="file://{1}" width="32"></td>' \
                    '<td width="100%" style="color:#660000; vertical-align:' \
                    'middle"><b>{0}</b></td></tr></table>'.format(
                    "This plugin is experimental", icn)

        if plugin_info.deprecated:
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
        path = plugin_info.library
        icon = plugin_info.icon
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

        html += "{0}</h1>".format(plugin_info.name)
        try:
            html += "<h5>{0}</h5>".format(plugin_info.description)
        except UnicodeEncodeError:
            html += "<h5>{0}</h5>".format(repr(plugin_info.description))

        if plugin_info.longDescription:
            about = plugin_info.longDescription
            html += about#.replace('\n', "<br/>")

        html += "<br/><br/>"
        if plugin_info.kind:
            html += "{0}: {1} <br/>".format("Kind", plugin_info.kind)
        # if metadata["tags"]:
        #     html += "{0}: {1} <br/>".format("Tags", metadata["tags"])
        if plugin_info.url or plugin_info.issuesUrl or plugin_info.codeUrl:
            html += "{0}: ".format("More info")
            if plugin_info.url:
                html += "<a href='{0}'>{1}</a> &nbsp; ".format(
                    plugin_info.url, "url")
            if plugin_info.issuesUrl:
                html += "<a href='{0}'>{1}</a> &nbsp; ".format(
                    plugin_info.issuesUrl, "issue tracker")
            if plugin_info.codeUrl:
                html += "<a href='{0}'>{1}</a>".format(
                    plugin_info.codeUrl, "source code")
            html += "<br/>"
        html += "<br/>"

        # if metadata.author.:
        #     html += "{0}: <a href='mailto:{1}'>{2}</a>".format(
        #         "Author", metadata.author_email, metadata.author_name)
        #     html += "<br/><br/>"
        if plugin_info.author:
            html += "{0}: {1}".format("Author", plugin_info.author)
            html += "<br/><br/>"

        if plugin_info.version:
            if plugin_info.version:
                ver = plugin_info.version
                if ver == "-1":
                    ver = '?'
                html += "Installed version: {0} (in {1})<br/>".format(
                    ver, path)
        if plugin_info.versionAvailable:
            html += "Available version: {0} (in {1})<br/>".format(
                plugin_info.versionAvailable, plugin_info.zipRepository)
        if plugin_info.changelog:
            html += "<br/>"
            changelog = "changelog:<br/>{0} <br/>".format(plugin_info.changelog)
            html += changelog.replace('\n', "<br/>")

        html += "</td></tr></table>"
        html += "</body>"

        eg.pluginManagerDialog.ShowPluginDetails(html)
        self.AdoptButtons(plugin_info)

    def AdoptButtons(self, plugin_info):
        #  Set buttonInstall text (and sometimes focus)
        if plugin_info.status == "upgradeable":
            eg.pluginManagerDialog.SetButtonLabel(
                "PM_btn_Install", "Upgrade Plugin")
        elif plugin_info.status == "newer":
            eg.pluginManagerDialog.SetButtonLabel(
                "PM_btn_Install", "Downgrade Plugin")
        elif plugin_info.status == "not installed" or \
                plugin_info.status == "new":
            eg.pluginManagerDialog.SetButtonLabel(
                "PM_btn_Install", "Install Plugin")
        else:
            # Default (will be grayed out if not available for reinstallation)
            eg.pluginManagerDialog.SetButtonLabel(
                "PM_btn_Install", "Reinstall Plugin")

        # Enable/disable buttons
        core = plugin_info.kind == "core"
        eg.pluginManagerDialog.EnableButton(
            "PM_btn_Install",
            (
                plugin_info.status != "orphan" or (
                    plugin_info.status != "not installed" and
                    plugin_info.status != "new"
                )
            ) and not core
        )
        eg.pluginManagerDialog.EnableButton(
            "PM_btn_Uninstall",
            plugin_info.status in ["newer", "upgradeable", "installed"]  # "orphan"
        )
        # hide = not ((metadata.status == "not installed") or
        #         (metadata.status == "new") and not core)
        # self.btn_uninstall.Show(hide)

    @eg.LogIt
    def reloadAndExportData(self):
        """ Reload All repositories and export data to the Plugin Manager """
        self.fetchAvailablePlugins(reloadMode=True)
        eg.pluginManagerDialog.UpdateRepositoriesList(self.repositories)

    @eg.LogIt
    def onManagerClose(self):
        """ Call this method when closing manager window.
        It resets last-use-dependent values. """
        self.plugins.updateSeenPluginsList()

    @eg.LogIt
    def upgradeAllUpgradeable(self):
        """ Reinstall all upgradeable plugins """
        for key in self.plugins.GetAllUpgradeable():
            self.installPlugin(key)

    @eg.LogIt
    def installPlugin(self, guid):
        """ Install given plugin """
        pluginInfo = self.plugins.GetAll()[guid]
        if not pluginInfo:
            return
        if pluginInfo.status == "newer" and not pluginInfo.error:
            # ask for confirmation if user downgrades an usable plugin
            rc = eg.MessageBox(
                "Are you sure you want to downgrade the "
                "plugin to the latest available version? "
                "The installed one is newer!",
                PM_NAME,
                parent=eg.pluginManagerDialog,
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
                    parent=eg.pluginManagerDialog,
                    style=wx.OK | wx.ICON_ERROR
                )
            else:
                eg.MessageBox(
                    "Downloaded file is corrupted! "
                    "The plugin will not be installed.\n"+repr(sys.exc_info()),
                    PM_NAME,
                    parent=eg.pluginManagerDialog,
                    style=wx.OK | wx.ICON_ERROR
                )
            return
        self.UpdateLists()
        eg.MessageBox(
            "Plugin '{0}' was successfully installed.\n"
            "Now you can add it to your configuration tree."
            .format(pluginInfo.name),
            PM_NAME,
            parent=eg.pluginManagerDialog,
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
            eg.MessageBox(parent=eg.pluginManagerDialog,
                message=eg.text.General.deletePlugin,
                caption=PM_NAME,
                style=wx.NO_DEFAULT | wx.OK | wx.ICON_EXCLAMATION,
            )
            return

        if guid in self.plugins.GetAll():
            pluginInfo = self.plugins.GetAll()[guid]
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
                parent=eg.pluginManagerDialog,
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
            parent=eg.pluginManagerDialog,
            style=wx.OK | wx.ICON_INFORMATION
        )

    def UpdateLists(self):
        # update the list of plugins in plugin handling routines
        self.plugins.ScanAllInstalledPlugins()
        self.plugins.rebuild()
        eg.pluginManagerDialog.UpdatePluginList()

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

    def __init__(self, plugins):
        #self.gui = gui
        self.plugins = plugins
        self.repositories = {}
        self.httpId = {}   # {httpId : repoName}
        self.PopulateRepoList()
        #self.gui.Bind(EVT_REPOSITORY_FETCHED, self.OnRepositoryFetched)

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
        if Config.check_interval == 0:
            return True
        try:
            lastDate = self.GetLastStartDay()
            interval = (wx.DateTime_Today() - lastDate).days
        except (ValueError, AssertionError):
            interval = 1
        return interval >= Config.check_interval

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
                    repo["state"],
                    repo["verify"]
                ])
            Config.repositories = repos

    def FetchRepositories(self):
        all_enabled_repos = self.GetEnabledRepos()
        if Config.check_on_start \
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
        eg.pluginManagerDialog.Bind(
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
                msg, PM_NAME, parent=eg.pluginManagerDialog,
                style=wx.OK | wx.ICON_ERROR
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
                msg, PM_NAME, parent=eg.pluginManagerDialog,
                style=wx.OK | wx.ICON_ERROR
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
        wx.PostEvent(eg.pluginManagerDialog, RepositoryFetched(repo=repo))
        # is the checking done?
        if not self.fetchingInProgress():
            wx.PostEvent(eg.pluginManagerDialog, CheckingDone())


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
        try:
            return self.local_cache[guid]
        except KeyError:
            pass
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
    def GetAll(self):
        """ return all plugins """
        return self.plugin_cache

    @eg.LogIt
    def GetAllInstalled(self):
        """ return all installed plugins """
        return {
            guid: self.plugin_cache[guid] for guid in self.local_cache
            }

    @eg.LogIt
    def GetAllNotInstalled(self):
        """ return all plugins that are not installed """
        return {
            guid: self.plugin_cache[guid] for guid in self.plugin_cache if
                guid not in self.local_cache
            }

    @eg.LogIt
    def GetAllUpgradeable(self):
        """ return all upgradeable plugins """
        return {key: self.plugin_cache[key] for key in self.plugin_cache if
                self.plugin_cache[key].status == "upgradeable"}

    @eg.LogIt
    def GetAllNew(self):
        """ return all new plugins """
        self._update_seen = True
        return {guid: self.plugin_cache[guid] for guid in self.plugin_cache if
                self.plugin_cache[guid].status == "new"}

    @eg.LogIt
    def GetAllInvalid(self):
        """ return all invalid plugins """
        plugins = {guid: self.plugin_cache[guid] for guid in self.plugin_cache if
                (self.plugin_cache[guid].status in ["orphan", "broken"]
                 or self.plugin_cache[guid].deprecated)
                }
        return plugins

    @eg.LogItWithReturn
    def GetGuidByUrl(self, name):
        """ Return first guid found for given url """
        plugins = [guid for guid in self.plugin_cache if self.plugin_cache[guid].download_url == name]
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
                version_available = parse_version(plugin.versionAvailable)

                newer_version_available = False
                if already_in_plugin_cache:
                    ver_in_cache = parse_version(
                        self.plugin_cache[guid].version
                    )
                    newer_version_available = version_available > ver_in_cache

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
                    elif ver_in_cache > version_available:
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

