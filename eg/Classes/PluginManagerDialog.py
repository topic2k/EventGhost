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

import wx
import wx.html
import wx.html2
import wx.lib.agw.infobar as IB
import wx.lib.agw.ultimatelistctrl as ULC
import wx.lib.newevent
import wx.richtext
from wx.lib.splitter import MultiSplitterWindow

import eg
from .PluginManagerSettings import ALL_PLUGINS_LABEL, Config, DEFAULT_VIEW, \
    PLUGIN_DETAILS_HTML_STYLE, VIEWS


egtext = eg.text.PluginManager.Dialog

UPDATE_CHECK_CHOICES = {
    0: egtext.Intervall_0,
    1: egtext.Intervall_1,
    3: egtext.Intervall_3,
    7: egtext.Intervall_7,
    14: egtext.Intervall_14,
    30: egtext.Intervall_30
}

LB_SORT_ASCENDING = 1
LB_SORT_DESCENDING = 2
LB_SORT_BY_NAME = 4
LB_SORT_BY_DOWNLOADS = 8
LB_SORT_BY_VOTE = 16
LB_SORT_BY_STATUS = 32
LB_SORT_BY_RELEASE_DATE = 64


@eg.LogIt
def OnEventCheckbox(event, cfg_attr):
    setattr(Config, cfg_attr, event.IsChecked())
    event.Skip()


@eg.LogIt
def OnIntervalChange(event):
    value = event.GetString()
    for interval, text in UPDATE_CHECK_CHOICES.iteritems():
        if value == text:
            Config.check_interval = interval
            break


@eg.LogIt
def GetCheckingInterval():
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
            # fallback to 1 day by default
            interval = 1
    if interval < 0:
        interval = 1
    allowed = UPDATE_CHECK_CHOICES.keys()
    allowed.sort(reverse=True)
    for j in allowed:
        if interval >= j:
            interval = j
            break
    Config.check_interval = interval
    return interval


@eg.LogIt
def UpdateView(lst, guid):
    view = eg.pluginManagerDialog.GetViewType()
    if view != ALL_PLUGINS_LABEL:
        DoViewChange()
    else:
        for item_id in range(lst.GetItemCount()):
            item_guid = lst.GetItemData(item_id)
            if item_guid == guid:
                lst.Select(item_id)
                break


@eg.LogIt
def OnUninstall(event):
    lst = wx.FindWindowByName("PM_PluginList")
    selected = lst.GetFirstSelected()
    if selected == -1:
        return
    guid = lst.GetItem(selected).GetData()
    eg.pluginManager.UninstallPlugin(guid)
    UpdateView(lst, guid)


@eg.LogIt
def OnInstall(event):
    lst = wx.FindWindowByName("PM_PluginList")
    guid = lst.GetItem(lst.GetFirstSelected()).GetData()
    eg.pluginManager.InstallPlugin(guid)
    UpdateView(lst, guid)


@eg.LogIt
def OnUpgradeAll(event):
    pass


@eg.LogIt
def OnViewChange(event):
    DoViewChange(event.GetString())


@eg.LogIt
def DoViewChange(view_type=None):
    if not view_type:
        view_type = eg.pluginManagerDialog.GetViewType()
    info = PLUGIN_DETAILS_HTML_STYLE + VIEWS[view_type]["desc"]
    eg.pluginManagerDialog.ShowPluginDetails(info)
    eg.pluginManagerDialog.EnableButton("PM_btn_Install", False)
    eg.pluginManagerDialog.EnableButton("PM_btn_Uninstall", False)
    eg.pluginManagerDialog.UpdatePluginList()


def StaticCheckBox(parent, label, message, name, cfg_attr):
    sb = wx.StaticBox(parent)
    chkbox = wx.CheckBox(sb, wx.ID_ANY, label, name=name)
    if cfg_attr:
        chkbox.SetValue(getattr(Config, cfg_attr))
        chkbox.Bind(wx.EVT_CHECKBOX, lambda event: OnEventCheckbox(event, cfg_attr))
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
              eg.APP_NAME, eg.PM_NAME
          )

    sb = wx.StaticBox(parent)
    chk = wx.CheckBox(
        sb, wx.ID_ANY, "Check for plugin updates",
        name="PM_chk_OnShow"
    )
    chk.Bind(wx.EVT_CHECKBOX, lambda event: OnEventCheckbox(
        event, "check_on_start"
    ))
    chc = wx.Choice(sb, wx.ID_ANY, choices=UPDATE_CHECK_CHOICES.values())
    chc.SetStringSelection(UPDATE_CHECK_CHOICES[GetCheckingInterval()])
    chc.Bind(wx.EVT_CHOICE, OnIntervalChange)
    info_text = IB.AutoWrapStaticText(sb, msg)
    info_text.SetSizeHints(-1, 50)

    szrH = wx.BoxSizer(wx.HORIZONTAL)
    szrH.Add(chk, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
    szrH.Add(chc, 0, wx.ALL, 5)

    szr = wx.StaticBoxSizer(sb, wx.VERTICAL)
    szr.Add(szrH, 0, wx.ALL, 5)
    szr.Add(info_text, 0, wx.ALL | wx.EXPAND, 5)
    return szr


def BoxRepositories(parent):
    sb = wx.StaticBox(parent)
    sb.Hide()
    lstRepo = ULC.UltimateListCtrl(sb, wx.ID_ANY, agwStyle=wx.LC_REPORT,
                                   name="PM_ctrl_Repos")
    lstRepo.InsertColumn(0, "Status")
    lstRepo.InsertColumn(1, "Name")
    lstRepo.InsertColumn(2, "URL")

    btnAdd = wx.Button(sb, wx.ID_ANY, "Add", name="PM_btn_Add")
    btnEdit = wx.Button(sb, wx.ID_ANY, "Edit...", name="PM_btn_Edit")
    btnDelete = wx.Button(sb, wx.ID_ANY, "Delete", name="PM_btn_Delete")
    btnRepload = wx.Button(sb, wx.ID_ANY, "Reload repository",
                           name="PM_btn_Reload")

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


class PanelPluginList(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelPluginList, self).__init__(*args, **kwargs)

        chc_views = wx.Choice(
            self, wx.ID_ANY, choices=VIEWS.keys(),
            name="PM_lst_Views"
        )
        chc_views.Bind(wx.EVT_CHOICE, OnViewChange)
        chc_views.SetSelection(0)

        ulc_plugins = ULC.UltimateListCtrl(
            self, wx.ID_ANY,
            agwStyle=ULC.ULC_REPORT | ULC.ULC_SINGLE_SEL | ULC.ULC_NO_HEADER,
            name="PM_PluginList"
        )
        ulc_plugins.InsertColumn(0, "plugin")
        ulc_plugins.SetColumnWidth(0, ULC.ULC_AUTOSIZE_FILL)
        ulc_plugins.Bind(
            ULC.EVT_LIST_ITEM_SELECTED,
            eg.pluginManager.OnPluginSelected
        )

        srchLabel = wx.StaticText(self, wx.ID_ANY, "Search")
        searchTxt = wx.TextCtrl(self, wx.ID_ANY, name="PM_ctrl_Search")
        searchTxt.Bind(wx.EVT_TEXT_ENTER, self.OnSearch)

        szrSearch = wx.BoxSizer(wx.HORIZONTAL)
        szrSearch.Add(srchLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        szrSearch.Add(searchTxt, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(chc_views, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)
        szr.Add(ulc_plugins, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        szr.Add(szrSearch, 0, wx.ALL | wx.EXPAND, 5)
        szr.Hide(szrSearch, True)
        self.SetSizer(szr)
        self.Layout()

    @staticmethod
    def OnSearch(event):
        event.Skip()


class PanelDetailsAndAction(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelDetailsAndAction, self).__init__(*args, **kwargs)

        html_details = wx.html2.WebView.New(
            self, wx.ID_ANY,
            name="PM_html_PluginDetails"
        )
        html_details.SetPage(
            PLUGIN_DETAILS_HTML_STYLE +
            VIEWS[DEFAULT_VIEW]["desc"], ""
        )

        btn_upgrade_all = wx.Button(
            self, wx.ID_ANY, "Updgrade all", name="PM_btn_UpgradeAll"
        )
        btn_upgrade_all.Disable()
        btn_upgrade_all.Bind(wx.EVT_BUTTON, OnUpgradeAll)

        btn_uninstall = wx.Button(
            self, wx.ID_ANY, "Uninstall plugin", name="PM_btn_Uninstall"
        )
        btn_uninstall.Disable()
        btn_uninstall.Bind(wx.EVT_BUTTON, OnUninstall)

        btn_install = wx.Button(
            self, wx.ID_ANY, "Install plugin", name="PM_btn_Install"
        )
        btn_install.Disable()
        btn_install.Bind(wx.EVT_BUTTON, OnInstall)

        szr_btns= wx.BoxSizer(wx.HORIZONTAL)
        szr_btns.Add(btn_upgrade_all, 0, wx.ALL, 5)
        szr_btns.AddSpacer((0, 0), 1, wx.EXPAND, 5)
        szr_btns.Add(btn_uninstall, 0, wx.ALL, 5)
        szr_btns.Add(btn_install, 0, wx.ALL, 5)

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(html_details, 1, wx.ALL | wx.EXPAND, 5)
        szr.Add(szr_btns, 0, wx.EXPAND, 5)
        self.SetSizer(szr)
        self.Layout()


class PanelSettings(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelSettings, self).__init__(*args, **kwargs)

        sb_interval = BoxUpdateIntervall(self)
        msg = "NOTE: Experimental plugins are generally unsuitable for " \
              "production use. These plugins are in early stages of " \
              "development, and should be considered 'incomplete' or " \
              "'proof of concept' tools. The EventGhost Project does not " \
              "recommend installing these plugins unless you intend to " \
              "use them for testing purposes."

        sbExperimental = StaticCheckBox(
            self, message=msg, name="PM_chk_Experimental",
            label="Show also experimental plugins",
            cfg_attr="allow_experimental"
        )

        msg = "NOTE: Deprecated plugins are generally unsuitable for " \
              "production use. These plugins are unmaintained, and should " \
              "be considered 'obsolete' tools. The EventGhost Project does " \
              "not recommend installing these plugins unless you still need " \
              "it and there are no other alternatives available."
        sbDeprecated = StaticCheckBox(
            self, message=msg, name="PM_chk_Deprecated",
            label="Show also deprecated plugins",
            cfg_attr="allow_deprecated"
        )

        sbRepositories = BoxRepositories(self)

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(sb_interval, 0, wx.ALL | wx.EXPAND, 5)
        szr.Add(sbExperimental, 0, wx.ALL | wx.EXPAND, 5)
        szr.Add(sbDeprecated, 0, wx.ALL | wx.EXPAND, 5)
        szr.Add(sbRepositories, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(szr)
        self.Layout()


class PluginManagerDialog(wx.Frame):
    @eg.LogIt
    def __init__(self, *args, **kwargs):
        super(PluginManagerDialog, self).__init__(None, title=eg.PM_NAME)

        self._sortmode = LB_SORT_ASCENDING | LB_SORT_BY_NAME

        notebook = wx.Notebook(self, wx.ID_ANY)
        page_plugins = MultiSplitterWindow(
            notebook, style=wx.SP_LIVE_UPDATE
        )
        page_settings = PanelSettings(notebook)

        pnlPluginlist = PanelPluginList(page_plugins)
        pnlDetailsAndAction = PanelDetailsAndAction(page_plugins)
        page_plugins.AppendWindow(pnlPluginlist, 180)
        page_plugins.AppendWindow(pnlDetailsAndAction)

        notebook.AddPage(page_plugins, "Plugins", True)
        notebook.AddPage(page_settings, "Settings", False)

        self.Bind(wx.EVT_CLOSE, self.OnDlgClose)

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(notebook, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(szr)
        self.SetSize((650, 550))
        self.Layout()

        self.Bind(wx.EVT_SHOW, self.AfterShown)

    @eg.LogIt
    def AfterShown(self, event):
        event.Skip()
        wx.CallAfter(self.Refresh)

    @eg.LogIt
    def OnDlgClose(self, event):
        eg.pluginManager.onManagerClose()
        eg.pluginManagerDialog.Hide()

    @eg.LogIt
    def UpdatePluginList(self, sortmode=None):
        if not sortmode:
            sortmode = self._sortmode
        self._sortmode = sortmode

        plugins = VIEWS[self.GetViewType()]["func"]()
        plugin_list = []
        for info in plugins.itervalues():
            plugin_list.append(info)

        if sortmode & LB_SORT_BY_NAME:
            self.SortByName(plugin_list)
        elif sortmode & LB_SORT_BY_STATUS:
            self.SortByStatus(plugins)
        else:
            self._sortmode = LB_SORT_BY_NAME | LB_SORT_ASCENDING
            self.SortByName(plugin_list)

        if self._sortmode & LB_SORT_DESCENDING:
            plugin_list.reverse()
        self.RefreshList(plugin_list)

    @staticmethod
    @eg.LogIt
    def SortByName(plugins):
        plugins.sort(cmp=lambda x, y: cmp(x.name, y.name))

    @staticmethod
    @eg.LogIt
    def SortByStatus(plugins):
        plugins.sort(cmp=lambda x, y: cmp(x.status, y.status))

    @staticmethod
    @eg.LogIt
    def RefreshList(plugins):
        ulc = wx.FindWindowByName("PM_PluginList")
        ulc.Freeze()
        ulc.DeleteAllItems()
        for info in plugins:
            idx = ulc.Append([info.name])
            item = ulc.GetItem(idx)
            item.SetData(info.guid)
            if info.error:
                item.SetTextColour(wx.Colour(0, 136, 0))
                item.SetBackgroundColour(wx.Colour(255, 255, 136))
            elif info.experimental:
                item.SetTextColour(wx.Colour(102, 0, 0))
                item.SetBackgroundColour(wx.Colour(238, 238, 187))
            elif info.deprecated:
                item.SetTextColour(wx.Colour(102, 0, 0))
                item.SetBackgroundColour(wx.Colour(238, 187, 204))
            elif info.status == "upgradeable":
                # item.SetTextColour(wx.Colour(136, 0, 0))
                item.SetBackgroundColour(wx.Colour(255, 255, 170))
            elif info.status == "new":
                # item.SetTextColour(wx.Colour(0, 136, 0))
                item.SetBackgroundColour(wx.Colour(204, 255, 204))
            elif info.status == "newer":
                # item.SetTextColour(wx.Colour(0, 136, 0))
                item.SetBackgroundColour(wx.Colour(255, 255, 204))
            ulc.SetItem(item)
        ulc.Thaw()

    @staticmethod
    @eg.LogIt
    def UpdateRepositoriesList(repositories):
        lst = wx.FindWindowByName("PM_ctrl_Repos")
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

    @staticmethod
    def ShowPluginDetails(plugin_details_html):
        html_details = wx.FindWindowByName("PM_html_PluginDetails")
        html_details.SetPage(plugin_details_html, "")

    @staticmethod
    def EnableButton(button, enable):
        btn = wx.FindWindowByName(button)
        btn.Enable(enable)

    @staticmethod
    def GetViewType():
        lst = wx.FindWindowByName("PM_lst_Views")
        return lst.GetStringSelection() or DEFAULT_VIEW

    @staticmethod
    def SetButtonLabel(button, label):
        btn = wx.FindWindowByName(button)
        btn.SetLabel(label)

    def AdoptButtons(self, plugin_info):
        #  Set buttonInstall text (and sometimes focus)
        if plugin_info.status == "upgradeable":
            self.SetButtonLabel(
                "PM_btn_Install", "Upgrade Plugin")
        elif plugin_info.status == "newer":
            self.SetButtonLabel(
                "PM_btn_Install", "Downgrade Plugin")
        elif plugin_info.status == "not installed" or \
                plugin_info.status == "new":
            self.SetButtonLabel(
                "PM_btn_Install", "Install Plugin")
        else:
            # Default (will be grayed out if not available for reinstallation)
            self.SetButtonLabel(
                "PM_btn_Install", "Reinstall Plugin")

        # Enable/disable buttons
        core = plugin_info.kind == "core"
        self.EnableButton(
            "PM_btn_Install",
            (
                plugin_info.status != "orphan" or (
                    plugin_info.status != "not installed" and
                    plugin_info.status != "new"
                )
            ) and not core
        )
        self.EnableButton(
            "PM_btn_Uninstall",
            plugin_info.status in ["newer", "upgradeable", "installed"]  # "orphan"
        )
