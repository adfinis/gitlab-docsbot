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

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer


# init logging
logger = logging.getLogger('adsy-autodocs')
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        self.project = False
        self.git = gitlab.Gitlab( gitlab_url, gitlab_token, ssl_verify=False )

    def select_project_search(self, project_name):
        project = self.git.projects.search(project_name)
        if len(project)<1:
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
            # save git api url
            git_urlsave = self.git._url
            # set gitlab url to main for downloading artifact
            self.git._url = "{0}/".format(self.gitlab_url)
            # download artifact
            dl = self.git._raw_get(last_build.download_url)
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



def process_request(data):
    """
    Function to process an request from GitLab
    """

    global conf
    logger.info("Process build trigger")
    trigger_repo = data['project_name'].replace(" / ", "/")
    do_download = False
    extract_to = False

    # loop over every repo in config and see if it matches
    for repo in conf['repos']:
        if repo['name'] == trigger_repo:
            extract_to = repo['extract_to']
        try:
            if data['build_stage'] in repo['stages']:
                do_download = True
        except:
            do_download = True

    # download artifacts if found in config
    if do_download:
        logger.info("Found in config, download and extract artifacts for project #{0}".format(data['project_id']))
        dl_path = tempfile.mkdtemp()
        artifacts_zip = "{0}/artifacts.zip".format(dl_path)

        # wait some time until artifacts are uploaded
        time.sleep(25)

        # download artifacts
        ci = GitlabArtifactsDownloader(conf['gitlab']['url'], conf['gitlab']['token'])
        ci.select_project(data['project_id'])
        ci.download_last_artifacts(artifacts_zip)
        ci.unzip(artifacts_zip, dl_path)

        # remove artifacts zip
        os.remove(artifacts_zip)

        # copy artifacts to configured dir
        copy_tree(dl_path, extract_to)

        # remove temporary dir
        shutil.rmtree(dl_path)

        logger.info("Download artifacts of project #{0} done".format(data['project_id']))




class RequestHandler(BaseHTTPRequestHandler):
    """
    Class to handle incoming HTTP requests
    """

    def send_headers(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
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
            if (data['object_kind'] == "build" and data['build_status']=='success'):
                thread = threading.Thread( target=process_request, args=[data] )
                thread.start()
        except:
            pass

        self.send_headers()


def main():
    global conf
    # load config
    with open(sys.argv[1]) as f:
        conf = yaml.load(f)
    try:
        # start an http server
        server = HTTPServer(('', conf['autodocs']['port']), RequestHandler )
        logger.info("Started server on port {0}".format(conf['autodocs']['port']))
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()



if __name__ == "__main__":
    main()
