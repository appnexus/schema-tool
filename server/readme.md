# Schema Server

__Server__ is the persistent component, and real functionality of, the
command line tool and should be considered the primary way of extending
and/or integrating with the schema tools. The command line tools are
only simple wrappers around the server APIs with the caveat that invoking
the tooling results in an ephemeral version of the server custom configured
for the current working directory.


## Running the Server

The server is started with the command line (one of the few commands that does
not rely on the server :-) ) via:

```bash
$ schema server start [options]

#> Initializing schema server...
#> Validating configuration...
#> Located available port: 43782
#> Starting server at 0.0.0.0:43782
```

The server sub-command comes with a variety of sub-commands and options but
also excellent documentation with the `--help` flag. Feel free to use this
flag on the top-level `server` command or any of the sub-commands.

```bash
$ schema server --help
$ schema server start --help
```

## Configuring the Server

Server configuration is either read through environment variables or through
the same configuration file used by other parts of the command-line tool. All
server commands are under the `server` namespace in the config, ex:

```toml
[server]
port = 8182
```

The same rules apply for how / where this configuration file is loaded.

All configuration values have an environment variable counterpart that takes
priority over anything specified within the configuration file. The following
table defines all available configurations. Please note that all TOML config
values are defined under the `server` namespace as shown above that that all
environment variables are prefixed with `SCHEMA_SERVER_`. These are not included
below for brevity / ease of reading.

TOML Config Value | Environment Variable | Default | Description
------------------|----------------------|---------|------------
`port`            | `PORT`               | any available TCP port | Port server runs on. If not specified, any free TCP port may be chosen.


## Server API Docs

> TODO: Write docs for API endpoints (or auto-generate some docs)