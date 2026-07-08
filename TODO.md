# TODO

## Completed

### ~~Add support for locations parameter~~ (Done)

Implemented in the `proxy` module. Users can now define custom location blocks
with `path`, `forward_scheme`, `forward_host`, `forward_port`, and `advanced_config`.

### ~~Add access_list module~~ (Done)

New `access_list` module supports HTTP Basic auth entries and IP-based allow/deny rules.

## Future Enhancements

### Add support for more DNS providers for certificates

Currently only `domainoffensive` is supported for automated Let's Encrypt certificate
creation. Other popular providers (Cloudflare, Route53, etc.) could be added.

### Add dead_hosts module

NPM supports "dead hosts" (404 pages for specific domains). A module to manage these
would complete the coverage of all NPM host types.

### Add streams module

NPM supports TCP/UDP stream proxying. A module to manage streams would be useful
for non-HTTP services.
