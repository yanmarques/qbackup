# qbackup

An automated backup solution for qubes VMs.

My problem? It's to send scheduled `QubesOS` backups to a remote server through ssh.
I present here a reasonably secure service to address that problem.

# Table of contents

* [Read carefully](#read-carefully)
* [Installation](#installation)
* [Setup](#setup)
* [Example](#example)

# Read carefully

One should be advised that, as a general rule, _to manually audit source code of apps from unknow sources, like github, before actually run it_.

There are 3 main files for the 3 components of the backup infrastructure.

1. [qbackup](src/qbackup): installed in dom0
2. [qubes.BackupCarrier](src/qubes.BackupCarrier): installed in TemplateVM (or AppVM with qubes-bind-dirs) which has access to the remote server through ssh
3. [qbackup-shell](src/qbackup-shell): installed in the remote ssh server

There is an (recomended) apparmor profile for the `qbackup-shell`.

# Installation

The installation is executed for the 3 infrastructure components. The order which the installation is performed does not matter.

## Dom0

Copy `src/qbackup` script to dom0. Assuming one wants to execute `qbackup` as a cronjob or anacron, the script should exist at `/usr/bin/` directory or other directory allowed in `PATH` system environment variable. The script must be an executable with `chmod 755 /usr/bin/qbackup`, for example.

## TemplateVM

This VM will be the template of the AppVM which contains the keys to access the remote ssh server. Now, download the source code into a DispVM and copy it to the desired TemplateVM. Open a terminal and `cd` into the source code then execute the following command to install:

```bash
$ sudo make templatevm
```

Shutdown the TemplateVM.

## Backup Server

The backups goes to an account in the server. Save the desired user name of the account in your head for later. This account has a very special shell, that ideally only allows copying files to the home directory.

Download the source code and execute as root the following command to install (passing a `user` argument with the name of your account user name):

```bash
$ make server user=backup-awesome-user
```

The account shell was designed to be protected against most Remote Command Injection and Path Traversal (which would allow abitrary file writes). Althought, it's recommended to limit privileges of the shell executable with an AppArmor profile. If this is what one wants, execute the following command as root:

```
$ make server-aa
```

# Setup

After installed, one must configure the following:

## AppVM

The ssh server client. The configuration is the environment variable `SSH_CONN`. The best way to configure this is defining the variable at `~/.bashrc`. Example:

```bash
SSH_CONN=backup-awesome-user@remote.server.my
```

## Dom0

These configurations are not required, because one can provide them at command line. But if one wants a user wide setup, configure environments variables at `~/.bashrc`. The following variables are available (there is no need to export them):

- `QBKP_DEST_VM`: AppVM name where backups are sent to. This VM is not a regular one, it must have the qbackup service for TemplateVMs. For more information see (#installation/templatevm).
- `QBKP_PASS_FILE`: File containing the passphrase for `qvm-backup` tool. 

# Example

Backups in QubesOS are executed in Dom0. If one wants scheduled backups, Dom0 is the best place for it. Imagine one wants to backup `vault` AppVM in a cronjob:

```bash
 * * * * * your-user-name qbackup -f my-prefix- -t backups-vm -p /etc/bkp-passphrase.txt vault
```

Summary:

- `-f`: string prepended to the backup name in the remote server. It can contains a directory provided that the remote server already contains such directory (ie.: appvms/my-prefix-).
- `-t`: destination VM of the backup. If not provided tries to read from environment variable `QBKP_DEST_VM`.
- `-p`: file containing the passphrase for `qubes-backup` tool. If not provided tries to read from environment variable `QBKP_PASS_FILE`.
- `vault`: receives a list of arguments with the AppVMs to backup. 

If one wants to see logging information, filter journald logs with:

```bash
$ sudo journalctl -f | grep qbackup
```

