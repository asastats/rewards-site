# ASA Stats Rewards website

[![build-status](https://github.com/asastats/rewards-site/actions/workflows/build.yml/badge.svg)](https://github.com/asastats/rewards-site/actions/workflows/build.yml) [![build-contract](https://github.com/asastats/rewards-site/actions/workflows/build-contract.yml/badge.svg)](https://github.com/asastats/rewards-site/actions/workflows/build-contract.yml) [![docs](https://app.readthedocs.org/projects/rewards-site/badge/?version=latest)](https://rewards-site.readthedocs.io/en/latest/?badge=latest) [![codecov](https://codecov.io/gh/asastats/rewards-site/graph/badge.svg?token=DQC4SRY8J9)](https://codecov.io/gh/asastats/rewards-site) ![ansible-lint](https://github.com//asastats/rewards-site/actions/workflows/ansible-lint.yml/badge.svg) ![molecule](https://github.com/asastats/rewards-site/actions/workflows/molecule.yml/badge.svg) 

A website dedicated to ASA Stats contributions. Previously written in Laravel, now powered by Django.

## Usage

It provides a preview for all historic and latest contributions, hot tasks, contributions guide and more. Community members can use our [Discord Bot](https://github.com/asastats/rewards-site/tree/main/rewardsweb/rewardsbot) to suggest rewards for contributions which appear on this website.

> [!IMPORTANT]
> In order for the bot to access all the channels in the ASA Stats Discord, an admin has to assign it the `Verified` role.

### Environment variables

Environment variables shouldn't reside in repository, so `.env` files has to be created based on `.env-example`:

- Website's variables are placed in `rewardsweb/.env`.
- Discord bot's variables are placed in `rewardsweb/rewardsbot/.env`.
- Rewards smart contract's variables are placed in `rewardsweb/rewards/.env`.
- Please check `deploy/.env-example` for deployment variables.

> [!NOTE]
> If ADMIN_*_MNEMONIC variable is not set in `rewardsweb/rewards/.env`, then the system will treat the logged-in superuser as the admin. You will then need to assign the admin's public address to that superuser.

## Goals

- Stimulate community engagement 
- Provide a nice contributions overview
- Make the process of suggesting and collecting rewards straightforward
- Have a nice overview and documentation of contribution/reward process

## Roadmap

- [x] Initialize Django project on this repository
- [x] Setup environment: docker (optional), database, env file(s)
- [x] Create data models and migrations
- [x] Adjustment of script for contributions spreadsheet parsing
- [x] Create script for seeding the database with parsed data
- [x] Create API routes
- [x] Create methods for managing http requests and bind them to API routes
- [x] Automated documentation building and publishing on Read The Docs platform
- [x] Create methods for CRUD operations
- [x] Implement authentication by connecting a wallet
- [x] Create deploy workflow
- [x] Create smart contract for rewards allocation and claiming
- [x] Develop UI for rewards allocation and claiming
- [x] Implement additional issue trackers besides GitHub
- [ ] Create trackers and related parsers for messages with mentions on social media (X and reddit)
- [ ] Setup a server and deploy the application
