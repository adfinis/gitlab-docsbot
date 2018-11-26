#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#
#

import gitlab
import requests
import logging
import time
import threading
import yaml
import json

import os
import sys
import zipfile
import tempfile
import shutil
from distutils.dir_util import copy_tree

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


# init logging
logger = logging.getLogger('adsy-autodocs')
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                                  '%(message)s')
ch = logging.StreamHandler()
ch.setFormatter(log_formatter)
logger.setLevel(20)
logger.addHandler(ch)


class GitlabArtifactsDownloader:
    """
    Class to download and exract build aritfacts from gitlab
    """

    def __init__(self, gitlab_url, gitlab_token):
        # disable annoying sslcontext warnings
        requests.packages.urllib3.disable_warnings()
        self.gitlab_url = gitlab_url
        self.gitlab_token = gitlab_token
        self.project = False
        self.git = gitlab.Gitlab(gitlab_url, gitlab_token, ssl_verify=False)

    def select_project_search(self, project_name):
        project = self.git.projects.search(project_name)
        if len(project) < 1:
            self.project = False
            return False
        else:
            self.project = project[0]
            return True

    def select_project(self, project_id):
        self.project = self.git.projects.get(project_id)

    def download_last_artifacts(self, local_filename):
        if self.project:
            # fetch last build from api
            builds = self.project.builds.list()
            last_build = builds[0]
            artifacts_dl_url = "{0}/builds/{1}/artifacts/download".format(
                self.project.path_with_namespace, last_build.id)
            # save git api url
            git_urlsave = self.git._url
            # set gitlab url to main for downloading artifact
            self.git._url = "{0}/".format(self.gitlab_url)
            # download artifact
            dl = self.git._raw_get(artifacts_dl_url)
            # restore original api error
            self.git._url = git_urlsave
            self.save_download(dl, local_filename)

    def save_download(self, dl, local_filename):
        f = open(local_filename, 'wb')
        # loop over all chunks and append them to file
        for chunk in dl.iter_content(chunk_size=512 * 1024):
            # filter out keepalive packages
            if chunk:
                f.write(chunk)
        f.close()
        return

    def unzip(self, filename, extract_to):
        try:
            with zipfile.ZipFile(filename, "r") as z:
                z.extractall(extract_to)
        except:
            pass

    def download_raw_file(self, path):
        req_url     = "{0}/{1}".format(self.gitlab_url, path)
        req_headers = { "Private-Token": self.gitlab_token }
        dl          = requests.get(req_url, headers=req_headers) 
        return dl


def process_request(data):
    """
    Function to process an request from GitLab
    """

    global conf
    logger.info("Process build trigger")

    # pprint.pprint(data)

    git = GitlabArtifactsDownloader(conf['gitlab']['url'],
                                    conf['gitlab']['token'])

    repo = "/".join(data['repository']['homepage'].split("/")[3:])
    config_file = "/{0}/raw/{1}/.docs-bot.yml".format(repo, data['ref'])

    try:
        repo_conf_dl = git.download_raw_file(config_file)
        rc = yaml.load(repo_conf_dl.text)
        repo_conf = rc['docs']
    except:
        logger.error("config for repo not found")
        return

    try:
        allowed_path = False
        for candidate in conf['autodocs']['allowed_paths']:
            if repo_conf['extract_to'].startswith(candidate):
                allowed_path = True
    except:
        logger.error("Error parsing .docs-bot.yml")
        return

    if not allowed_path:
        logger.error("Extract path not allowed")
        return

    if not os.path.exists(repo_conf['extract_to']):
        os.mkdir(repo_conf['extract_to'])

    if 'stages' in repo_conf:
        if data['build_stage'] not in repo_conf['stages']:
            logger.info('do not fetch, stage does not match')
            return

    if 'download_delay' in repo_conf:
        logger.info("Config has delay in it, sleep for {0} secs".format(
            repo_conf['download_delay']))
        time.sleep(repo_conf['download_delay'])

    # now we are ready to fetch
    dl_path = tempfile.mkdtemp()
    artifacts_zip = "{0}/artifacts.zip".format(dl_path)
    git.select_project(data['project_id'])
    git.download_last_artifacts(artifacts_zip)
    git.unzip(artifacts_zip, dl_path)
    # remove artifacts zip
    os.remove(artifacts_zip)
    # copy artifacts to configured dir
    copy_tree(dl_path, repo_conf['extract_to'], update=1)
    # remove temporary dir
    shutil.rmtree(dl_path)
    logger.info("Download artifacts of project #{0} done".format(
        data['project_id']))
    return


class RequestHandler(BaseHTTPRequestHandler):
    """
    Class to handle incoming HTTP requests
    """

    def send_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("")

    def do_GET(self):
        self.send_headers()
        return

    def do_POST(self):
        global conf
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(data_string)
        try:
            if (data['object_kind'] == "build" and
                    data['build_status'] == 'success'):
                thread = threading.Thread(target=process_request, args=[data])
                thread.start()
        except:
            pass

        self.send_headers()

    def log_message(self, format, *args):
        logstr = (" ".join(map(str, args)))
        logger.info("REQUEST: {0}".format(logstr))


def main():
    global conf
    # load config
    with open(sys.argv[1]) as f:
        conf = yaml.load(f)
    try:
        # start an http server
        server = HTTPServer(('', conf['autodocs']['port']), RequestHandler)
        logger.info("Started server on port {0}".format(
            conf['autodocs']['port']))
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()


if __name__ == "__main__":
    main()
