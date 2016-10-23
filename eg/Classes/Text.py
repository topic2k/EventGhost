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

# Local imports
import eg
from eg.Utils import SetDefault

class Default:
    class General:
        configTree = "Configuration Tree"
        deleteQuestion = "Are you sure you want to delete this item?"
        deleteManyQuestion = (
            "This element has %s subelements.\n\n"
            "Are you sure you want to delete them all?"
        )
        deletePlugin = (
            "This plugin is used by actions in your configuration. You "
            "cannot remove it before all actions that are using this plugin "
            "have been removed."
        )
        deleteLinkedItems = (
            "At least one item outside your selection refers to an "
            "item inside your selection. If you continue to delete "
            "this selection, the referring item won't work properly "
            "anymore.\n\n"
            "Are you sure you want to delete the selection?"
        )
        ok = "OK"
        cancel = "Cancel"
        apply = "&Apply"
        yes = "&Yes"
        no = "&No"
        help = "&Help"
        choose = "Choose"
        browse = "Browse..."
        test = "&Test"
        pluginLabel = "Plugin: %s"
        autostartItem = "Autostart"
        unnamedFolder = "<unnamed folder>"
        unnamedMacro = "<unnamed macro>"
        unnamedEvent = "<unnamed event>"
        unnamedFile = "<unnamed file>"
        #moreTag = "more..."
        supportSentence = "Support for this plugin can be found"
        supportLink = "here"
        settingsPluginCaption = "Plugin Item Settings"
        settingsActionCaption = "Action Item Settings"
        settingsEventCaption = "Event Item Settings"
        noOptionsAction = "This action has no options to configure."
        noOptionsPlugin = "This plugin has no options to configure."
        monitorsLabel = "Identified monitors:"
        monitorsHeader = (
            "Monitor nr.",
            "X coordinate",
            "Y coordinate",
            "Width",
            "Height",
        )

        smartSpinMenu = (
            'Change control to "Spin Num"',
            'Change control to "Text" with {eg.result}',
            'Change control to "Text" with {eg.event.payload}',
            'Change control to (empty) "Text"'
        )
        smartSpinTooltip = (
            "Use the right mouse button\n"
            "to open the context menu!"
        )

    class Error:
        FileNotFound = "File \"%s\" couldn't be found."
        InAction = 'Error in Action: "%s"'
        pluginNotActivated = 'Plugin "%s" is not activated'
        pluginStartError = "Error starting plugin: %s"
        pluginLoadError = "Error loading plugin file: %s"
        configureError = "Error while configuring: %s"

    class Plugin:
        pass

    class PluginManager:
        Author = "Author"
        AvailableVersion = "Available version"
        Changelog = "Changelog"
        Deprecated = "This plugin is deprecated"
        Downgrade = \
            "Are you sure you want to downgrade the " \
            "plugin to the latest available version? " \
            "The installed one is newer!"
        ErrorBrokenPlugin = "This plugin is broken."
        ErrorConnectingRepo = "Couldn't connect to repository:"
        ErrorIncompatible1 =\
            "This plugin is incompatible with this version of {0}.\n"
        ErrorIncompatible2 = "The Plugin is designed for {0} {1}."
        ErrorMissingModule = "This plugin requires a missing module."
        ErrorParsingRepoData = "Error while parsing data from repository."
        ErrorReadingRepo = "Error reading repository: {0}\n\n{1}"
        ErrorWrongFormat = \
            "Data from repository has wrong format.\n" \
            "Missing Key:"
        Experimental = "This plugin is experimental"
        FetchingRepos = "fetching repositories..."
        FileCorrupt = "Downloaded file is corrupted!\n" \
                      "The plugin will not be installed."
        In = "in"
        InstalledVersion = "Installed version"
        NewPluginsAvailable = \
            "There are new plugins available.\nYou can " \
            "install and get information about them in " \
            "the Plugin Manager."
        NewerPlugin =\
            "Installed version of this plugin is higher than" \
            " any version found in repository"
        NewPlugin = "This is a new plugin"
        NewVersionAvailable = "There is a new version available"
        NoDetails = "No details available"
        NotAvailable = \
            "Warning: this plugin isn't available in any accessible " \
            "repository!\nAre you sure you want to uninstall plugin\n" \
            "'{0}' (version {1})?"
        ObsoletePlugin = \
            "Obsolete plugin:\n{0}\n\n" \
            "EventGhost has detected an obsolete plugin that masks " \
            "its more recent version shipped with this copy of " \
            "EventGhost. Do you want to remove the old plugin right " \
            "now and unmask the more recent version?"
        OfficialRepoName = "Official EventGhost Plugin Repository"
        PluginRemoveFailed = \
            "Removing plugin failed!\n" \
            "Path: {0}\n" \
            "Function: {1}\n" \
            "Exception information:\n{2}"
        PluginStatusAmbiguous1 = "Error: plugin status is ambiguous (1)"
        PluginStatusAmbiguous2 = \
            "Error: plugin status is ambiguous (2)" \
            "\n-----------------------------------------------" \
            "\nplugin: {0} ({1})" \
            "\nself.plugin_cache[key].status = {2}" \
            "\nself.plugin_cache[key].installed = {3}"
        Removed = "Plugin '{0}' was removed successfully."
        Success = \
            "Plugin '{0}' was successfully installed.\n" \
            "Now you can add it to your configuration tree."

        class Dialog:
            Intervall_0 = "on every call of PluginManager"
            Intervall_1 = "once a day"
            Intervall_3 = "every 3 days"
            Intervall_7 = "every week"
            Intervall_14 = "every 2 weeks"
            Intervall_30 = "every month"
            LabelAllPlugins = "All plugins"
            LabelInstalled = "Installed plugins"
            LabelNotInstalled = "Not installed plugins"
            LabelUpgradeable = "Upgradeable plugins"
            LabelNew = "New plugins"
            LabelInvalid = "Invalid plugins"
            InfoAll = """<h3>All Plugins</h3>
                <p>
                On the left you see the list of all plugins available for
                your {0}, both installed and available for download.
                Some plugins come with your {0} installation while
                most of them are made available via the plugin repositories.
                </p>

                <p>
                You can temporarily enable or disable a plugin.
                To <i>enable</i> or <i>disable</i> a plugin, click its
                checkbox or doubleclick its name...
                </p>

                <p>
                Plugins showing in <span style='color:red'>red</span> are
                not loaded because there is a problem. They are also listed
                on the 'Invalid' tab. Click on the plugin name to see more
                details, or to reinstall or uninstall this plugin.
                </p>
                """
            InfoInstalled = """<h3>Installed Plugins</h3>
                <p>
                Here you only see plugins <b>installed</b> in {0}.
                </p>
                <p>
                Click on the name to see details.
                </p>
                <p>
                Click the checkbox or doubleclick the name to <i>activate</i>
                or <i>deactivate</i> the plugin.
                </p>
                <p>
                You can change the sorting via the context menu (right click).
                </p>
                """
            InfoNotInstalled = """<h3>Not installed plugins</h3>
                <p>
                Here you see the list of all plugins available in the
                repositories, but which are <b>not yet installed</b>.
                </p>
                <p>
                Click on the name to see details.
                </p>
                <p>
                You can change the sorting via the context menu (right click).
                </p>
                <p>
                A plugin can be downloaded and installed by clicking on
                it's name, and then click the 'Install' button.
                </p>
                """
            InfoUpgradeable = """<h3>Upgradeable plugins</h3>
            <p>
            Here are <b>upgradeable plugins</b>. It means, more recent
            versions of installed plugins are available in the repositories.
            </p>
            """
            InfoNew = """<h3>New plugins</h3>
            <p>
            Here you see <b>new</b> plugins which were released
            since you last visited this list.
            </p>
            """
            InfoInvalid = """<h3>Invalid plugins</h3>
            <p>
            Plugins in this list here are <b>broken or incompatible</b>
            with your version of {0}.
            </p>

            <p>
            Click on an individual plugin; if possible {0} shows
            you more information.
            </p>

            <p>
            The main reasons to have invalid plugins, is that this plugin is
            not build for this version of {0}. Maybe you can download another
            version from <a href="http://www.eventghost.net/downloads/">
            www.eventghost.net</a>.
            </p>

            <p>
            Another common reason is that a plugin needs some external python
            libraries (dependencies). You can install them yourself,
            depending on your operating system. After a correct install,
            the plugin should work.
            </p>
            """

    class MainFrame:
        onlyLogAssigned = "&Log only assigned and activated events"
        onlyLogAssignedToolTip = (
            "If checked, the log will only show events that would actually\n"
            "execute in the current configuration, so you should uncheck\n"
            "this when you want to assign new events."
        )

        class TaskBarMenu:
            Show = "&Show EventGhost"
            Hide = "&Hide EventGhost"
            Exit = "E&xit"

        class Menu:
            FileMenu = "&File"
            New = "&New"
            Open = "&Open..."
            Save = "&Save"
            SaveAs = "Save &As..."
            Options = "O&ptions..."
            Restart = "&Restart"
            Exit = "E&xit"

            EditMenu = "&Edit"
            Undo = "&Undo"
            Redo = "&Redo"
            Cut = "Cu&t"
            Copy = "&Copy"
            Python = "Copy as P&ython"
            Paste = "&Paste"
            Delete = "&Delete"
            SelectAll = "Select &All"
            Find = "&Find..."
            FindNext = "Find &Next"

            ViewMenu = "&View"
            HideShowToolbar = "&Toolbar"
            ExpandAll = "&Expand All"
            CollapseAll = "&Collapse All"
            ExpandOnEvents = "Select on E&xecution"
            LogMacros = "Log &Macros"
            LogActions = "Log &Actions"
            LogDebug = "Log &Debug Info"
            IndentLog = "&Indent Log"
            LogTime = "Time&stamp Log"
            ClearLog = "Clear &Log"

            ConfigurationMenu = "&Configuration"
            AddPlugin = "Add Plugin..."
            AddFolder = "Add Folder"
            AddMacro = "Add Macro..."
            AddEvent = "Add Event..."
            AddAction = "Add Action..."
            Configure = "Configure Item"
            Rename = "Rename Item"
            Execute = "Execute Item"
            Disabled = "Disable Item"

            HelpMenu = "&Help"
            HelpContents = "&Help Contents"
            WebHomepage = "Home &Page"
            WebForum = "Support &Forums"
            WebWiki = "&Wiki"
            PythonShell = "P&ython Shell"
            CheckUpdate = "Check for &Updates..."
            About = "&About EventGhost..."

            Apply = "&Apply Changes"
            Close = "&Close"
            Export = "&Export..."
            Import = "&Import..."
            Replay = "&Replay"
            Reset = "&Reset"

        class SaveChanges:
            mesg = (
                "Configuration contains unsaved changed.\n\n"
                "Do you want to save before continuing?"
            )
            saveButton = "&Save"
            dontSaveButton = "Do&n't Save"

        class Logger:
            caption = "Log"
            welcomeText = "---> Welcome to EventGhost <---"

        class Tree:
            caption = "Configuration"

        class Messages:
            cantAddEvent = (
                "Events can only be added to macros."
            )
            cantAddAction = (
                "Actions can only be added to macros and Autostart."
            )
            cantDisable = (
                "The root item and Autostart can't be disabled."
            )
            cantRename = (
                "The root item, Autostart, and plugins can't be renamed."
            )
            cantExecute = (
                "The root item, folders, and events can't be executed."
            )
            cantConfigure = (
                "Only plugins, events, and actions can be configured."
            )


def Text(language):
    class Translation(Default):
        pass
    languagePath = os.path.join(eg.languagesDir, "%s.py" % language)
    try:
        eg.ExecFile(languagePath, {}, Translation.__dict__)
    except IOError:
        pass
    SetDefault(Translation, Default)
    return Translation
