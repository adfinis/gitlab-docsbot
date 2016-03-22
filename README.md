# GitLab CI automated docs sync

This script starts an simple server which accepts requests from GitLab Webhooks,
and downloads artifacts from lastest build to an configured directory.

## Installation

```
apt-get install python-setuptools python-pip python-yaml
python setup.py install
systemctl daemon-reload
systemctl enable gitlab-autodocs.service
```

## Configuration

### Initial
Add an new user in GitLab called `docs-bot` and get his API-Key.
Then edit `/etc/gitlab-autodocs.yaml` and set your GitLab-URL, and the API-Key.

### Add new repos to sync

You need to create an `.docs-bot.yml` in your repository, example

```
docs:
  extract_to: /var/www/docs/autodocs-ci-test
  download_delay: 10
  stages:
    - docs
```
`docs` needs to be the root entry of `y.docs-bot.yml`
- `extract_to` directory to put artifacts
- `download_delay` since gitlab triggers before uploading artifacts, you can configure an delay before fetching here
- `stages` if defined, only snyc specified build stages configured in `.gitlab-ci.yml`


In GitLab, you need to grant `docs-bot` access to your repo and add an new Webhook which triggers on build-events, pointing to your docsync url.
