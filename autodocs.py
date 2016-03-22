#!/usr/bin/env python
# -*- coding: utf-8 -*-

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import os
import gitlab
import time
import threading
import yaml
import sys
import tempfile
import requests
import zipfile
import shutil
import json
from distutils.dir_util import copy_tree
import pprint

import logging

logger = logging.getLogger('adsy-autodocs')
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(log_formatter)
logger.setLevel(20)
logger.addHandler(ch)


class gitlab_artifacts_downloader:
    """
    Class to download and exract build aritfacts from gitlab
    """

    def __init__(self, gitlab_url, gitlab_token):
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
            builds = self.project.builds.list()
            last_build = builds[0]
            git_urlsave = self.git._url
            self.git._url = "{0}/".format(self.gitlab_url)
            dl = self.git._raw_get(last_build.download_url)
            self.git._url = git_urlsave
            self.save_download(dl, local_filename)

    def save_download(self, dl, local_filename):
        f = open(local_filename, 'wb')
        for chunk in dl.iter_content(chunk_size=512 * 1024):
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



class trigger_processer():
    """
    Class to process incoming http requests
    """

    def __init__(self, data):
        self.data = data

    def process(self):
        global conf

        logger.info("Process build trigger")
        trigger_repo = self.data['project_name'].replace(" / ", "/")

        do_download = False
        extract_to = False

        for repo in conf['repos']:
            
            if repo['name'] == trigger_repo:
                extract_to = repo['extract_to']
                try:
                    if self.data['build_stage'] in repo['stages']:
                        do_download = True
                except:
                    do_download = True

        if do_download:
            logger.info("Found in config, download and extract artifacts for project #{0}".format(self.data['project_id']))
            dl_path = tempfile.mkdtemp()
            artifacts_zip = "{0}/artifacts.zip".format(dl_path)

            # wait some time until artifacts are uploaded
            time.sleep(25)

            # download artifacts
            ci = gitlab_artifacts_downloader(conf['gitlab']['url'], conf['gitlab']['token'])
            ci.select_project(self.data['project_id'])
            ci.download_last_artifacts(artifacts_zip)
            ci.unzip(artifacts_zip, dl_path)

            # remove artifacts zip
            os.remove(artifacts_zip)

            # copy artifacts to configured dir
            copy_tree(dl_path, extract_to)

            # remove temporary dir
            shutil.rmtree(dl_path)

            logger.info("Download artifacts of project #{0} done".format(self.data['project_id']))





class request_handler(BaseHTTPRequestHandler):
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
                proc = trigger_processer( data )
                thread = threading.Thread( target = proc.process )
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
        server = HTTPServer(('', conf['autodocs']['port']), request_handler )
        logger.info("Started server on port {0}".format(conf['autodocs']['port']))
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()



if __name__ == "__main__":
    main()
