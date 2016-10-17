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
import sys
from os.path import exists, join

from pkg_resources import parse_version

import eg


class PluginModuleInfo(object):
    """
    Holds information of a plugin module.

    The main purpose of this class is to get the information from the
    eg.RegisterPlugin call inside the plugin module. So it imports the main
    module, but stops the import immediately after the eg.RegisterPlugin call.
    """
    name = u"Unknown Plugin"
    description = u""
    author = u""
    version = u""
    kind = u"other"
    guid = ""
    canMultiLoad = False
    createMacrosOnAdd = False
    icon = eg.Icons.PLUGIN_ICON
    url = None
    englishName = None  # TODO: needed why? (topic2k)
    englishDescription = None  # TODO: needed why? (topic2k)
    path = None
    pluginName = None
    hardwareId = ""
    valid = False
    # --- new ---
    longDescription = None
    pluginHelp = ""
    egVersion = ">={0}.{1}".format(eg.Version.major, eg.Version.minor)  # use pip versionChecker (e.g. >0.4.0, <0.6.0)
    egMinVersion = "0.0.0"
    egMaxVersion = "999.999.999"
    experimental = False
    deprecated = False
    issuesUrl = None
    codeUrl = None
    changelog = None
    versionAvailable = ""
    zipRepository = ""
    download_url = None
    filename = ""
    available = False  # Will be overwritten, if any available version found.
    installed = False
    status = "unknown"  # Will be overwritten, if any available version found.
    dependencies = None

    def __init__(self, path, local_plugin=True):
        self.description = self.path = path
        self.name = self.pluginName = os.path.basename(path)
        if not local_plugin:
            return
        originalRegisterPlugin = eg.RegisterPlugin
        eg.RegisterPlugin = self.RegisterPlugin
        sys.path.insert(0, self.path)
        try:
            if self.path.startswith(eg.corePluginDir):
                moduleName = "eg.CorePluginModule." + self.pluginName
            else:
                moduleName = "eg.UserPluginModule." + self.pluginName
            if moduleName in sys.modules:
                # TODO: (topic2k) will this overwrite python modules?
                # why is it needed?
                del sys.modules[moduleName]
            __import__(moduleName, None, None, [''])
        except eg.Exceptions.RegisterPluginException:
            # It is expected that the loading will raise
            # RegisterPluginException because eg.RegisterPlugin() is called
            # inside the module
            self.status = "installed"
            self.valid = True
        except:
            if eg.debugLevel:
                eg.PrintTraceback(eg.text.Error.pluginLoadError % self.path)
        finally:
            del sys.path[0]
            eg.RegisterPlugin = originalRegisterPlugin

    if eg.debugLevel:
        def __setattr__(self, name, value):
            if not hasattr(self.__class__, name):
                raise AttributeError(
                    "%s has no attribute %s" % (self.__class__.__name__, name)
                )
            object.__setattr__(self, name, value)

    def RegisterPlugin(
        self,
        name = None,
        description = None,
        kind = u"other",
        author = u"",
        version = u"",
        icon = None,
        canMultiLoad = False,
        createMacrosOnAdd = False,
        url = None,
        help = None,
        guid = "",
        hardwareId = "",
        # --- new ---
        longDescription=None,
        experimental=False,
        deprecated=False,
        issuesUrl=None,
        codeUrl=None,
        pluginHelp=None,
        egVersion = ">={0}.{1}".format(eg.Version.major, eg.Version.minor),  # use pip versionChecker (e.g. >0.4.0, <0.6.0)
        egMinVersion="0.0.0",
        egMaxVersion="999.999.999",
        changelog=None,
        **kwargs
    ):
        self.experimental = experimental
        self.deprecated = deprecated
        self.issuesUrl = issuesUrl
        self.codeUrl = codeUrl
        self.egVersion = egVersion
        self.egMinVersion = egMinVersion
        self.egMaxVersion = egMaxVersion
        self.changelog = changelog
        self.versionAvailable = ""
        self.zipRepository = ""
        self.download_url = self.path
        self.filename = ""
        self.available = False  # Will be overwritten, if any available version found.
        self.installed = False
        self.status = "unknown"  # Will be overwritten, if any available version found.
        self.dependencies = None

        # Mark core plugins as readonly
        self.readOnly = self.path.startswith(eg.pluginDirs[0])

        if pluginHelp and not longDescription:
            self.longDescription = pluginHelp
        else:
            self.longDescription = longDescription
        if pluginHelp:
            pluginHelp = "\n".join([s.strip() for s in pluginHelp.splitlines()])
            pluginHelp = pluginHelp.replace("\n\n", "<p>")
            description += "\n\n<p>" + pluginHelp

        if not name:
            name = self.pluginName
        if not description:
            description = name
        if help:
            help = "\n".join([s.strip() for s in help.splitlines()])
            help = help.replace("\n\n", "<p>")
            description += "\n\n<p>" + help
        self.name = self.englishName = unicode(name)
        self.description = self.englishDescription = unicode(description)
        self.kind = unicode(kind)
        self.author = (
            unicode(", ".join(author)) if isinstance(author, tuple)
            else unicode(author)
        )
        error = None
        errorDetails = None
        eg_min = parse_version(egMinVersion)
        eg_max = parse_version(egMaxVersion)
        eg_ver = parse_version(eg.Version.base)
        if not (eg_min <= eg_ver <= eg_max):
            error = "incompatible"
            errorDetails = "{0} - {1}".format(egMinVersion, egMaxVersion)
        self.error = error
        self.error_details = errorDetails
        self.version = unicode(version)

        self.canMultiLoad = canMultiLoad
        self.createMacrosOnAdd = createMacrosOnAdd
        self.url = unicode(url) if url else url  # Added by Pako
        self.guid = guid.upper()
        if not guid:
            eg.PrintDebugNotice("missing guid in plugin: %s" % self.path)
            self.guid = self.pluginName
        self.hardwareId = hardwareId.upper()
        # get the icon if any
        if icon:
            self.icon = eg.Icons.StringIcon(icon)
        else:
            iconPath = join(self.path, "icon.png")
            if exists(iconPath):
                self.icon = eg.Icons.PathIcon(iconPath)

        # try to translate name and description
        textCls = getattr(eg.text.Plugin, self.pluginName, None)
        if textCls is not None:
            self.name = getattr(textCls, "name", name)
            self.description = getattr(textCls, "description", description)

        # we are done with this plugin module, so we can interrupt further
        # processing by raising RegisterPluginException
        raise eg.Exceptions.RegisterPluginException
