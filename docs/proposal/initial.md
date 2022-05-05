## Problem

Lack of a good granular automatic backups.

### Subproblem

1. I don't know which machines are currently in the loop of backups
2. The backup process is not tested nor clear
3. I want to be easy to add new vms in a backup group

## Current implementation

### Pros

- Automatic backups
- They kind of work

## Cons

- Lack of built-in vm backup by group
- It's very hard/annoying to add new vms to backup loop
- It's very hard to easily know which vms are in the which group for backups

## Requirements

1. Get all VMs per group
2. Manage group membership by VM with easy tool
3. Manage VM backup interval

## Optional features

1. Automatic crontab installation