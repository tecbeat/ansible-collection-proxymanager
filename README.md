# Ansible Collection - nils_ost.proxymanager

This repository contains the `nils_ost.proxymanager` Ansible Collection.

It came to life as I searched for a way to streamline automated installation and configuration of
[Nginx Proxy Manager](https://nginxproxymanager.com/) instances for different environments, but couldn't find a viable library/collection.
The project started out by develpoing local modules and roles for my playbooks, but as I like to use those on multiple projects it seamed
to be a good idea to outsource everything in a collection.
And thats it: A collection for my purposes but available for everyone who find a need in using it ;)

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against following Ansible versions: **>=2.13.9**.

For collections that support Ansible 2.9, please ensure you update your `network_os` to use the
fully qualified collection name (for example, `cisco.ios.ios`).
Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
<!--end requires_ansible-->

## External requirements

The `requests` Python library is required by this collection to communicate with the NPM REST API.
As all module calls should use `delegate_to: localhost`, install it locally:

```bash
pip install requests
```

## Architecture

The collection uses a shared HTTP client (`plugins/module_utils/client.py`) that provides:
- `NginxProxyManagerClient` - session-based HTTP client with typed error handling
- `authenticate()` - one-shot token exchange helper
- Common helpers (`compare_dicts`, `search_by_domain`) for idempotent operations

All CRUD modules share authentication options via `plugins/doc_fragments/auth.py`.

Use `ansible-doc nils_ost.proxymanager.<module>` to see full documentation for each module.

## Included content

<!--start collection content-->
### Modules
Name | Description
--- | ---
[nils_ost.proxymanager.token](https://github.com/nils-ost/ansible-collection-proxymanager/blob/main/docs/nils_ost.proxymanager.token_module.rst)|Authenticate with the NPM API and obtain a bearer token
[nils_ost.proxymanager.proxy](https://github.com/nils-ost/ansible-collection-proxymanager/blob/main/docs/nils_ost.proxymanager.proxy_module.rst)|Create, update, or delete proxy hosts (with locations, SSL, HSTS)
[nils_ost.proxymanager.redirection](https://github.com/nils-ost/ansible-collection-proxymanager/blob/main/docs/nils_ost.proxymanager.redirection_module.rst)|Create, update, or delete HTTP redirections
[nils_ost.proxymanager.certificate](https://github.com/nils-ost/ansible-collection-proxymanager/blob/main/docs/nils_ost.proxymanager.certificate_module.rst)|Create or delete SSL/TLS certificates (Let's Encrypt DNS-01)
[nils_ost.proxymanager.access_list](https://github.com/nils-ost/ansible-collection-proxymanager/blob/main/plugins/modules/access_list.py)|Create, update, or delete access lists (HTTP basic auth + IP rules)

<!--end collection content-->

### Roles

Name | Description
--- | ---
[nils_ost.proxymanager.install_with_docker](https://github.com/nils-ost/ansible-collection-proxymanager/blob/main/roles/install_with_docker/README.md)|installs Nginx Proxy Manager within docker
[nils_ost.proxymanager.basic_config](https://github.com/nils-ost/ansible-collection-proxymanager/blob/main/roles/basic_config/README.md)|configures Nginx Proxy Manager with basic capabilities

## Using this collection

```bash
ansible-galaxy collection install nils_ost.proxymanager
```

You can also include it in a `requirements.yml` file and install it via
`ansible-galaxy collection install -r requirements.yml` using the format:

```yaml
collections:
  - name: nils_ost.proxymanager
```

To upgrade the collection to the latest available version, run the following
command:

```bash
ansible-galaxy collection install nils_ost.proxymanager --upgrade
```

You can also install a specific version of the collection, for example, if you
need to downgrade when something is broken in the latest version (please report
an issue in this repository). Use the following syntax where `X.Y.Z` can be any
[available version](https://galaxy.ansible.com/nils_ost/proxymanager):

```bash
ansible-galaxy collection install nils_ost.proxymanager:==X.Y.Z
```

See
[Ansible Using Collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)
for more details.

## Release notes

> [!WARNING]
> **Breaking change:** on v2.0.0 the default path of `proxymanager_compose_dir` for role `install_with_docker` changed from `~/proxymanager` to `/opt/proxymanager`  
> If you previously used the default, consider now to overwrite the variable in your playbook with `~/proxymanager`  
> Or take down the compose stack in `~/proxymanager` and move the whole directory to `/opt/proxymanager`

See the
[changelog](CHANGELOG.md).

## Roadmap

This collection is mainly intended to be used by myself. Therefor I'm just developing the stuff I need for my current projects on a irregular basis.
But if you find some benefit in this collection, feel free to use it. If you like to have some features added feel free to create a pull-request
or write an issue with a feature-request and I'm going to see if I can make it happen.

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](LICENSE) to see the full text.
