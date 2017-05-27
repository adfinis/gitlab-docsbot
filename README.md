# GitLab CI Docs Bot

This script starts a simple web server which accepts requests from GitLab
webhooks and downloads artifacts from the latest build to a defined directory.

## Installation

```
# apt-get install python-setuptools python-pip python-yaml
# python setup.py install
# systemctl daemon-reload
# systemctl enable gitlab-autodocs
# systemctl start gitlab-autodocs
```

## Configuration

### Initial

Add a new user in GitLab called `docs-bot` and get his API-Key. Then edit 
`/etc/gitlab-autodocs.yaml` and set your GitLab URL and the API key.

### Add new repos to sync

You need to create a `.docs-bot.yml` in your repository, example:

```
docs:
  extract_to: /var/www/docs/autodocs-ci-test
  download_delay: 10
  stages:
    - docs
```

`docs` needs to be the root entry of `.docs-bot.yml`
- `extract_to` directory to put artifacts
- `download_delay` since GitLab triggers before uploading artifacts, you can
   configure a delay before fetching them
- `stages` if defined, only sync specified build stages configured in 
  `.gitlab-ci.yml`

In GitLab, you need to grant `docs-bot` access to your repo and add a new
webhook which triggers on build events, pointing to your docsync URL.
