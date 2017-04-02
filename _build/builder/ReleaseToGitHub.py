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

import base64
import sys
import wx
from agithub.GitHub import GitHub
from os.path import join

# Local imports
import builder
from builder.Utils import BuildError, IsCIBuild, NextPage

if sys.version_info[0:2] > (3, 0):
    import http.client
    import urllib.parse
else:
    import httplib as http
    http.client = http
    import urllib as urllib
    urllib.parse = urllib

class ReleaseToGitHub(builder.Task):
    description = "Release to GitHub"

    def Setup(self):
        self.enabled = bool(self.buildSetup.gitConfig["token"])
        if self.buildSetup.showGui:
            self.activated = False
        else:
            self.activated = (
                bool(self.buildSetup.args.release) and self.enabled
            )

    def DoTask(self):
        buildSetup = self.buildSetup
        appVer = "v" + buildSetup.appVersion
        gitConfig = buildSetup.gitConfig
        token = gitConfig["token"]
        user = gitConfig["user"]
        repo = gitConfig["repo"]
        branch = gitConfig["branch"]
        setupFile = 'EventGhost_{0}_Setup.exe'.format(buildSetup.appVersion)
        setupPath = join(buildSetup.outputDir, setupFile)
        self.chglogFile = "CHANGELOG.md"
        self.chglogShort = "CHANGELOG_THIS_RELEASE.md"
        chglogPath = join(buildSetup.outputDir, self.chglogFile)

        print "reading changelog"
        try:
            f = open(chglogPath, 'r')
        except IOError:
            print "ERROR: couldn't read changelog file ({0}).".format(self.chglogFile)
            return
        else:
            changelog = f.read()
            f.close()

        print "loading setup file"
        try:
            f = open(setupPath, 'rb')
        except IOError:
            print "ERROR: '{0}' not found.".format(setupFile)
            return
        else:
            setupFileContent = f.read()
            f.close()

        gh = GitHub(token=token)

        print "getting release info"
        releaseExists = False
        releaseId = None
        uploadUrl = None
        page = 1
        while page > 0:
            rc, data = gh.repos[user][repo].releases.get(
                sha=branch,
                per_page=100,
                page=page
            )
            page = NextPage(gh)
            if rc == 200:
                for rel in data:
                    if rel['name'] == appVer:
                        msg = (
                            "Found an existing GitHub release matching"
                            " '{0}'".format(appVer)
                        )
                        if IsCIBuild():
                            raise BuildError(msg)
                        app = wx.GetApp()
                        win = app.GetTopWindow()
                        dlg = wx.MessageDialog(
                            win,
                            caption="Information",
                            message=msg + "\nOverwrite it?",
                            style=wx.YES_NO
                        )
                        if dlg.ShowModal() == wx.ID_NO:
                            return
                        releaseId = rel["id"]
                        uploadUrl = str(rel['upload_url'][:-13])
                        releaseExists = True

        print "getting branch info"
        rc, data = gh.repos[user][repo].branches[branch].get()
        if rc != 200:
            raise BuildError("ERROR: couldn't get branch info.")
        commitSha = data['commit']['sha']
        # if not uploadUrl:
        #     uploadUrl = str(data['upload_url'][:-13])

        rc, data = gh.repos[user][repo].contents[self.chglogFile].get(ref=branch)
        if rc == 200:
            remoteChangelog = base64.decodestring(data["content"])
        else:
            remoteChangelog = None
        newCommitSha = None
        if changelog != remoteChangelog:
            newCommitSha = self.CommitChangelog(gh, commitSha, changelog)

        if not releaseExists:
            print "reading changelog for this release"
            try:
                f = open(join(buildSetup.outputDir, self.chglogShort), 'r')
            except IOError:
                print "ERROR: couldn't read changelog file ({0}).".format(
                    self.chglogShort)
                relChglog = ""
            else:
                relChglog = f.read().strip()
                f.close()

            # relChglog = ''
            # chgLines = changelog.splitlines(True)
            # try:
            #     for i in range(1, len(chgLines)):
            #         if chgLines[i].startswith("## "):
            #             break
            #         else:
            #             relChglog += chgLines[i]
            # except IndexError:
            #     pass
            # relChglog = relChglog.strip()

            print "creating release"
            body = dict(
                tag_name=appVer,
                target_commitish=newCommitSha,
                name=appVer,
                body=relChglog,
                draft=False,
                prerelease=("-" in self.buildSetup.appVersion)
            )
            rc, data = gh.repos[user][repo].releases.post(body=body)
            if rc != 201:
                raise BuildError(
                    "ERROR: couldn't create a release on GitHub."
                )
            uploadUrl = str(data['upload_url'][:-13])
        else:
            print 'deleting existing asset'
            rc, data = gh.repos[user][repo].releases[releaseId].assets.get()
            if rc == 200:
                for asset in data:
                    if asset["name"] == setupFile:
                        rc, data = gh.repos[user][repo].releases.\
                            assets[asset["id"]].delete()
                        if rc != 204:
                            print "ERROR: couldn't delete existing asset."
                            return
                        break

        print "uploading setup file"
        url = uploadUrl + '?name={0}'.format(setupFile)
        headers = {
            'content-type': 'application/octet-stream',
            'authorization': 'Token {0}'.format(token),
            'accept': 'application/vnd.github.v3+json',
            'user-agent': 'agithub/v2.0'
        }
        conn = http.client.HTTPSConnection('uploads.github.com')
        conn.request('POST', url, setupFileContent, headers)
        response = conn.getresponse()
        status = response.status
        conn.close()
        if status != 201:
            raise BuildError(
                "ERROR: couldn't upload installer file to GitHub."
            )

    def CommitChangelog(self, gh, commitSha, changelog):
        buildSetup = self.buildSetup
        appVer = "v" + buildSetup.appVersion
        gitConfig = buildSetup.gitConfig
        user = gitConfig["user"]
        repo = gitConfig["repo"]
        branch = gitConfig["branch"]
        ref = 'heads/{0}'.format(branch)

        print "getting commit referenced by branch"
        rc, data = gh.repos[user][repo].git.commits[commitSha].get()
        if rc != 200:
            raise BuildError("ERROR: couldn't get commit info.")
        treeSha = data['tree']['sha']

        print "getting tree"
        rc, data = gh.repos[user][repo].git.trees[treeSha].get()
        if rc != 200:
            raise BuildError( "ERROR: couldn't get tree info.")

        blob = None
        print "getting blob for {0}".format(self.chglogFile)
        for entry in data['tree']:
            if entry['path'] == self.chglogFile and entry['type'] == 'blob':
                blob = entry
                break
        if blob is None:
            raise BuildError( "ERROR: couldn't get blob info.")

        print "posting new changelog"
        body = dict(content=changelog, encoding='utf-8')
        rc, data = gh.repos[user][repo].git.blobs.post(body=body)
        if rc != 201:
            raise BuildError("ERROR: couldn't post new changelog contents.")

        print "posting tree"
        newblob = dict(
            path=blob['path'],
            mode=blob['mode'],
            type=blob['type'],
            sha=data['sha']
        )
        body = dict(tree=[newblob], base_tree=treeSha)
        rc, data = gh.repos[user][repo].git.trees.post(body=body)
        if rc != 201:
            raise BuildError("ERROR: couldn't post new tree.")
        newTreeSha = data['sha']

        print "creating commit for changelog update"
        body = {
            'message': "Add changelog for {0}".format(appVer),
            'tree': newTreeSha,
            'parents': [commitSha]
        }
        rc, data = gh.repos[user][repo].git.commits.post(body=body)
        if rc != 201:
            raise BuildError(
                "ERROR: couldn't create commit for changelog update."
            )
        newCommitSha = data['sha']

        print "updating reference for branch to new commit"
        body = dict(sha=newCommitSha)
        rc, data = gh.repos[user][repo].git.refs[ref].patch(body=body)
        if rc != 200:
            raise BuildError(
                "ERROR: couldn't update reference ({0}) "
                "with new commit.".format(ref)
            )

        return newCommitSha
