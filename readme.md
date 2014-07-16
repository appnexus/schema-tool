# Schema Tool

This tool is intended to help you manage your schemas in a framework agnostic
way that works well for both large and small teams. The tool helps in working with
complex data-models by enforcing an alter-chain to ensure that developers don't step
on each other's toes. Currently the tool supports MySQL and Postgres The key features
of the tool are:

+ Manage alter chains (parents and children) and provide check/resolve tools to enforce
+ Automatically run alters to setup, teardown, or rebuild database
+ Determine what environment alters are allowed to run in
+ Keep track of a history of what alters have been run in the DB for easy programatic usage

One thing that the tool is not, and does not try to be, is a DSL for making alters. SQL
is an excellent DSL already, so there is no need for that.why


## Requirements

+ Python 2.7 (may work with other versions, only tested against 2.7)
+ [`psycopg2`][3] installed if you plan to use with Postgres

## Getting Started

You need to download the tool and (preferrably) have the `schema` executable somewhere on
your path.You can get started with the tool simply by doing

> Note: Unlike previous versions, the tool does not have to be located with(in) the
> directory containing the alters you are working with.

```shell
mkdir -p ~/bin
cd ~/bin
git clone git@github.com:appnexus/schema-tool.git schema-tool

echo 'export PATH="$HOME/bin/schema-tool:$PATH"' >> ~/.bashrc
# or
echo 'alias schema="$HOME/bin/schema-tool/schema.py"' >> ~/.bashrc

source ~/.bashrc
```

If I am creating a new project I can simply do the following:

```shell
mkdir my-schemas
cd my-schemas/
git init

cp ~/bin/schema-tool/conf/config.json.mysql-template config.json
# or
cp ~/bin/schema-tool/conf/config.json.pgsql-template config.json

vim config.json #edit appropriately
```


Take a look at the mysql template config file and you'll see

```json
{
    "username": "root",
    "password": "root",
    "host": "localhost",
    "revision_db_name": "revision",
    "history_table_name": "history",
    "port": 3306,
    "type": "mysql"
}
```


It should be pretty self-explanatory except for the revision db and the history table. This is
where the tool is going to keep track of what alters have been ran. Feel free to choose whatever
names you like. Do know that the tool will take care of creating and DB and table.

Once you have this setup, you are ready to take a tour of the tool and create your first
alter. You can find all the commands supported by the tool by reading the help-file, which
you can get to via `schema -h`. You should see the following:

```text
Usage: schema command [options]

Commands:
  new         Create a new alter
  check       Check that all back-refs constitute a valid chain
  list        List the current alter-chain
  up          Bring up to particular revision
  down        Roll back to a particular revision
  rebuild     Run the entire database down and back up (hard refresh)
  gen-ref     Generate new file-ref
  gen-sql     Generate SQL for a given reference, including revision-history alter(s)
  resolve     Resolve a divergent-branch conflict (found by 'check' command)
  init        Initialize new project
  help        Show this help message and exit

Options:
  -h, --help  show this help message and exit
```

Additionally each command also has its own help file. For example, if you wanted to see what
options are available to you when applying an alter, you can could `schema up -h` and see

```text
Usage: schema up [options] [ref]

Arguments
  ref               Rn all alters up to, and including the ref given

Options:
  -h, --help        show this help message and exit
  -n N, --number=N  Run N number of up-alters from current state - overrides
                    arguments
  -f, --force       Continue running up-alters even if an error has occurred
  -v, --verbose     Output verbose error-messages when used with -f option if
                    errors are encountered
```

To get started and create our first file, we can simply run

```shell
schema init
schema new -f init
```

The `init` will take care of setting up the `revision` DB and `history` table (or whatever you
configured them to be) and any janitorial tasks. The `new` will create an up and a down-file
that will look something like this

```text
137823105930-init-down.sql
137823105930-init-up.sql
```

The number at the front is the identifier that is used to keep the alter-chain in line (see next
section on understanding the chain). We can now edit the files (including whatever alter you have)
and applying them against your local DB by running `schema up`.

Now you're up and running! You can add more files with `schema new` and control the state of your
DB with `up`, `down`, and `rebuild` commands.

## Understanding The Alter Chain

To understand how the tool does it's job, you have to understand how it thinks about alters.
When working with alters, it's easy to have dependencies between alters such that order is
very important. The way that the tool addresses this is by giving each alter a unique reference
and each alter specifies it's parent alter by their references. The parent-relationship
specifies that the parent alter should be applied before the child alter. This creates a singly
linked list where the tail is the first alter to be run and the head is the last alter to be
run.

```text
A <----- B <----- C <----- D <----- E <----- F
```

A valid alter-chain does not have any branching such that a parent has multiple children.
This can arise in situations where you might have created a separate feature-branch in your
version control system and merged it back to the mainline after some time of development in
which the mainline branch had advanced in the interim:

```text
A <----- B <----- C  <----- F
                  ^\
                    \ <----- D <----- E
```

The `check` command will alert you to any inconsistencies in your alter chain like that which
is defined above. The `resolve` command will help you resolve such issues if they are found.
More on that later.

I should also mention that each node in the alter-chain is actually a pair of alters.
One item in the pair is the up alter and the other item is the down alter. The actual structure
would look like:

```text
Up:    A <----- B <----- C <----- D <----- E <----- F
       ∧        ∧        ∧        ∧        ∧        ∧
       |        |        |        |        |        |
       ∨        ∨        ∨        ∨        ∨        ∨
Down:  A <----- B <----- C <----- D <----- E <----- F
```

The alters are given refs, rather than incremental numbers, because it makes things a
little easier to track within the DB in terms of what has been applied. When working with
multiple branches, the incremental numbers may not represent the correct set of alters that
have been applied to the DB. This is important when updating that we know we are up to date
with the correct alters.

## Running Alters (up / down / rebuild)

You can run alters by using the `up`, `down`, and `rebuild` commands. The `rebuild` command
will run all the way down and all the way back up. There are some common options you should
be aware of that each command supports:

+ `-v` outputs verbose error messages
+ `-f` will ignore errors and move on to running the next alter
+ `-n` (only on `up` and `down`) specifies the number of alters to run from current point
+ `ref` you can provide a reference number to run up/down to. For rebuild it will run down to
  this commit and back up (inclusively)

You may run into errors when switching branches often because the tool will get confused on
what may or may not have ran against your DB. Most of the time you can get around this by
running `schema rebuild -fv`.

## Checking and Resolving the Alter Chain

Running the `check` command will let you know if you have a divergent branch. Typically this
is the result of merging two branches or rebasing against your stable branch from your
feature branch. The `check` command will tell you where the branch occurs and list the two
alters that are in question. If you know which alter is at fault (typically the new alter)
then you can simply run

```shell
schema resolve OFFENDING_ALTER_HASH
```

This will move the offending alter (and any alters that come after it in the sub-chain)
to the end of the alter-chain. One thing to note is that if you resolve the incorrect
alter, then you may end up with an order-of events that does not make sense.

## DBA Alter Generation

If you work in a large organization or with a mission-critical RDBMS then your DBAs may,
understandably, be hesitant to use any tool to auto-magically run alters against the
production environment. However you likely still want to take advantage of the
revision-tracking functionality that tools of this sort typically provide. This tool
provides the best of both worlds. Your DBAs can use plain alters (and whatever tools
they choose) and you can track what revisions have run against your production DB. This
can be done with the `gen-sql` command.

The `gen-sql` command generates a set of alters, from your original alters, with SQL
added to manage the revision table on _up_ or _down_ alters. To get started we need to
ensure that our schema project is setup correctly for static alter genration.

> __Assumptions:__
> + All commands are performed within the root directory of the schema project that
    _you_ created (as per the __Getting Started__ section)
> + The `config.json` (config file) is located within the project root

+ Edit your config.json to include the following two keys:
```json
"static_alter_dir": "DBA_FILES/"
"pre_commit_hook": "pre-commit-hook-static-dba-files.sh"
```
+ Copy the pre-commit hook from the schema-tool's contrib to your schema-dir:
```shell
cp SCHEMA-TOOL-REPO/contrib/pre-commit-hook-static-dba-files.sh .
```
+ Use the schema-tool to install the hook and perform any needed setup:
```shell
schema init
```
+ Perform initial generation (for any existing alter):
```shell
schema gen-sql -qw
```

Now that you have the hook installed, you will see auto-generated files show up
each time you commit a new (or edit an existing) alter.


You can look at the help-file for `gen-sql` yourself to become familiar with the
other options of the command.

## Recommended Workflow

You can use the tool any way that you see fit. However, we've found that it works quite
well when you work with feature branches. In this workflow all new work is done on a feature
branch and `master` becomes the stable branch. When an atler is completed (tested / reviewed)
you can rebase against `master` and then run a `schema check` followed by a `schema resolve`
if necessary. When you merge to master you ensure that the feature branch is up-to-date.

In this way you avoid merges with `master` (and thus divergent alter-chains) and ensure that
`master` is clean (and ideally stable). You can further enforce this workflow with testing
(ensuring that all the alters can be run) such as [Jenkins][1] and [Gerrit][2] (to enforce
the rebase-based workflow).

## Reporting Issues / Feature Requests

If you run into an issue that results in a script error (Python stacktrace) then please
open up a ticket in the GitHub issue tracker. Please include the following information

+ Steps to reproduce issue
+ Entire error output including stack trace

We'll work with you to resolve the issue and collect any more information that may be
required to diagnose the issue.

## Contributing

If you would like to contribute, please see our current list of issues and/or feature requests
and send us a pull request. If you have something specific that you'd like to add or fix please
open up an issue for discussion. If it is a fix for a bug or everyone agrees that it would be
a useful feature, then submit your pull request. Make sure that your pull request's commit message
uses one of the [appropriate identifiers][4] to link the pull request to the issue.

[Current contributors][5]

## License

__ToDo__: Determine what license is appropriate




  [1]: http://jenkins-ci.org/
  [2]: https://code.google.com/p/gerrit/
  [3]: https://github.com/psycopg/psycopg2
  [4]: https://github.com/blog/1386-closing-issues-via-commit-messages
  [5]: https://github.com/appnexus/schema-tool/graphs/contributors
