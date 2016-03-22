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

You need to create an entry for every repo you want to snyc in `/etc/gitlab-autodocs.yaml`, for example:

```
  - name: Cyrill/autodocs-ci-test
    extract_to: /var/www/docs/autodocs-ci-test
    stages:
      - docs
```

- `name` defines the GitLab repo in format `group/repo`
- `extract_to` directory to put artifacts
- `stages` if defined, only snyc specified build stages configured in `.gitlab-ci.yml`

After adding an new entry, you need to run `systemctl restart gitlab-autodocs`

In GitLab, you need to grant `docs-bot` access to your repo and add an new Webhook which triggers on build-events, pointing to your docsync url.
