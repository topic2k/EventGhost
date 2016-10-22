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

from ObjectListView import ColumnDefn, ObjectListView

import eg
from .PluginManagerSettings import PLUGIN_DETAILS_HTML_STYLE, PM_NAME, \
    VIEWS, DEFAULT_VIEW, Config

UPDATE_CHECK_CHOICES = {
    0: "on every call of PluginManager",
    1: "once a day",
    3: "every 3 days",
    7: "every week",
    14: "every 2 weeks",
    30: "every month"
}

LB_SORT_ASCENDING = 1
LB_SORT_DESCENDING = 2
LB_SORT_BY_NAME = 4
LB_SORT_BY_DOWNLOADS = 8
LB_SORT_BY_VOTE = 16
LB_SORT_BY_STATUS = 32
LB_SORT_BY_RELEASE_DATE = 64


def OnEventCheckbox(event, cfg_attr):
    setattr(Config, cfg_attr, event.IsChecked())
    event.Skip()


def OnIntervalChange(event):
    value = event.GetString()
    for interval, text in UPDATE_CHECK_CHOICES.iteritems():
        if value == text:
            Config.check_interval = interval
            break


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
            # fallback do 1 day by default
            interval = 1
    if interval < 0:
        interval = 1
    # allowed values:
    allowed = UPDATE_CHECK_CHOICES.keys()
    allowed.sort(reverse=True)
    for j in allowed:
        if interval >= j:
            interval = j
            break
    Config.check_interval = interval
    return interval


def OnUninstall(event):
    lst = wx.FindWindowByName("PM_PluginList")
    guid = lst.GetItem(lst.GetFirstSelected()).GetData()
    eg.pluginManager.uninstallPlugin(guid)


def OnInstall(event):
    lst = wx.FindWindowByName("PM_PluginList")
    guid = lst.GetItem(lst.GetFirstSelected()).GetData()
    eg.pluginManager.installPlugin(guid)


def OnUpgradeAll(event):
    pass


def OnViewChange(event):
    DoViewChange(event.GetString())


@eg.LogIt
def DoViewChange(view_type=DEFAULT_VIEW):
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
              eg.APP_NAME, PM_NAME
          )

    sb = wx.StaticBox(parent)
    chk = wx.CheckBox(
        sb, wx.ID_ANY, "Check for plugin updates on startup",
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


class PanelViewSelection(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PanelViewSelection, self).__init__(*args, **kwargs)

        # lst_view = wx.ListBox(self, wx.ID_ANY, choices=VIEWS.keys(),
        #                       name="PM_lst_Views")
        lst_view = wx.Choice(
            self, wx.ID_ANY, choices=VIEWS.keys(),
            name="PM_lst_Views"
        )
        lst_view.Bind(wx.EVT_LISTBOX, OnViewChange)
        lst_view.SetSelection(0)

        szr = wx.BoxSizer()
        szr.Add(lst_view, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(szr)
        self.Layout()


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
            self, wx.ID_ANY,# size=(160,400),
            agwStyle=ULC.ULC_REPORT | ULC.ULC_SINGLE_SEL | ULC.ULC_NO_HEADER,
            name="PM_PluginList"
        )
        ulc_plugins.InsertColumn(0, "plugin")
        ulc_plugins.SetColumnWidth(0, ULC.ULC_AUTOSIZE_FILL)
        ulc_plugins.Bind(ULC.EVT_LIST_ITEM_SELECTED,
                     eg.pluginManager.OnPluginSelected)

        # lstPlugins = wx.ListBox(self, wx.ID_ANY, name="PM_PluginList")
        # lstPlugins.Bind(wx.EVT_LISTBOX, eg.pluginManager.OnPluginSelected)

        srchLabel = wx.StaticText(self, wx.ID_ANY, "Search")
        searchTxt = wx.TextCtrl(self, wx.ID_ANY, name="PM_ctrl_Search")
        searchTxt.Bind(wx.EVT_TEXT_ENTER, self.OnSearch)

        szrLst = wx.BoxSizer(wx.HORIZONTAL)
        # szrLst.Add(lstPlugins, 1, wx.EXPAND | wx.ALL, 5)
        szrLst.Add(ulc_plugins, 1, wx.EXPAND | wx.ALL, 5)

        szrSearch = wx.BoxSizer(wx.HORIZONTAL)
        szrSearch.Add(srchLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        szrSearch.Add(searchTxt, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(chc_views, 0, wx.EXPAND | wx.TOP, 5)
        szr.Add(szrLst, 1, wx.ALL | wx.EXPAND, 5)
        szr.Add(szrSearch, 0, wx.ALL | wx.EXPAND, 5)
        szr.Hide(szrSearch, True)
        self.SetSizer(szr)
        self.Layout()

    def OnSearch(self, event):
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
    def __init__(self, *args, **kwargs):
        #kwargs.update({"style": wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER})
        super(PluginManagerDialog, self).__init__(None, title=PM_NAME)

        self._sortmode = LB_SORT_ASCENDING | LB_SORT_BY_NAME

        maimain_bookBook = wx.Notebook(self, wx.ID_ANY)
        page_plugins = MultiSplitterWindow(
            maimain_bookBook, style=wx.SP_LIVE_UPDATE
        )
        page_settings = PanelSettings(maimain_bookBook)

        #pnlView = PanelViewSelection(page_plugins)
        pnlPluginlist = PanelPluginList(page_plugins)
        pnlDetailsAndAction = PanelDetailsAndAction(page_plugins)
        #page_plugins.AppendWindow(pnlView, 150)
        page_plugins.AppendWindow(pnlPluginlist, 180)
        page_plugins.AppendWindow(pnlDetailsAndAction)

        maimain_bookBook.AddPage(page_plugins, "Plugins", True)
        maimain_bookBook.AddPage(page_settings, "Settings", False)

        stLine = wx.StaticLine(self, wx.ID_ANY, style=wx.LI_HORIZONTAL)
        btnDlgOk = wx.Button(self, wx.ID_OK)
        btnDlgOk.Bind(wx.EVT_BUTTON, self.OnDlgOk, id=wx.ID_OK)
        btnDlgHelp = wx.Button(self, wx.ID_HELP)
        #btnDlgHelp.Bind(wx.EVT_BUTTON, self.OnDlgHelp, id=wx.ID_HELP)
        self.Bind(wx.EVT_CLOSE, self.OnDlgClose)

        szrDlgBtn = wx.StdDialogButtonSizer()
        szrDlgBtn.AddButton(btnDlgOk)
        szrDlgBtn.AddButton(btnDlgHelp)
        szrDlgBtn.Realize()

        szr = wx.BoxSizer(wx.VERTICAL)
        szr.Add(maimain_bookBook, 1, wx.EXPAND | wx.ALL, 5)
        szr.Add(stLine, 0, wx.EXPAND | wx.ALL, 5)
        szr.Add(szrDlgBtn, 0, wx.ALL | wx.EXPAND, 15)

        self.SetSizer(szr)
        self.SetSize((900, 680))
        self.Layout()

        self.html_details = self.FindWindowByName("PM_html_PluginDetails")
        self.Bind(wx.EVT_SHOW, self.AfterShown)

    def AfterShown(self, event):
        event.Skip()
        wx.CallAfter(self.Refresh)

    @eg.LogIt
    def OnDlgOk(self, event):
        eg.pluginManager.onManagerClose()
        self.Hide()

    @eg.LogIt
    def OnDlgClose(self, event):
        eg.pluginManager.onManagerClose()
        eg.pluginManagerDialog.Hide()

    # def OnListRightClick(self, event):
    #     menu_list = (
    #         (
    #             (LB_SORT_ASCENDING | LB_SORT_BY_NAME),
    #             "sort by name (ascending)"
    #         ),
    #         (
    #             (LB_SORT_DESCENDING | LB_SORT_BY_NAME),
    #             "sort by name (descending)"
    #         ),
    #         (
    #             (LB_SORT_ASCENDING | LB_SORT_BY_STATUS),
    #             "sort by status (ascending)"
    #         ),
    #         (
    #             (LB_SORT_DESCENDING | LB_SORT_BY_STATUS),
    #             "sort by status (descending)"
    #         ),
    #     )
    #
    #     mnu = wx.Menu()
    #     for wxid, label in menu_list:
    #         mnu.Append(wx.ID_HIGHEST + 1000 + wxid, label)
    #
    #     # self.Bind(wx.EVT_MENU, lambda event:
    #     #     self.OnPaste(rcRow, rcCol, text), mn)
    #     mnu.Bind(wx.EVT_MENU, self.OnListPopupMenu)
    #     self.PopupMenu(mnu)
    #     mnu.Destroy()
    #
    # def OnListPopupMenu(self, event):
    #     sortmode = event.GetId() - wx.ID_HIGHEST - 1000
    #     self.UpdatePluginList(sortmode)

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

    def SortByName(self, plugins):
        plugins.sort(cmp=lambda x, y: cmp(x.name, y.name))

    def SortByStatus(self, plugins):
        plugins.sort(cmp=lambda x, y: cmp(x.status, y.status))

    def RefreshList(self, plugins):
        # lst_plugins = wx.FindWindowByName("PM_PluginList")
        ulc = wx.FindWindowByName("PM_PluginList")
        ulc.Freeze()
        ulc.DeleteAllItems()
        # lst_plugins.Freeze()
        # lst_plugins.Clear()
        for info in plugins:
            # lst_plugins.Append(info.name, info.guid)
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
        # lst_plugins.Thaw()
        ulc.Thaw()

    def UpdateRepositoriesList(self, repositories):
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

    def ShowPluginDetails(self, plugin_details_html):
        self.html_details.SetPage(plugin_details_html, "")

    def SetButtonLabel(self, button, label):
        btn = wx.FindWindowByName(button)
        btn.SetLabel(label)

    def EnableButton(self, button, enable):
        btn = wx.FindWindowByName(button)
        btn.Enable(enable)

    def GetViewType(self):
        lst = wx.FindWindowByName("PM_lst_Views")
        return lst.GetStringSelection() or DEFAULT_VIEW
