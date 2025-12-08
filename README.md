# Rewards Suite

[![build-status](https://github.com/asastats/rewards-suite/actions/workflows/build.yml/badge.svg)](https://github.com/asastats/rewards-suite/actions/workflows/build.yml) [![build-contract](https://github.com/asastats/rewards-suite/actions/workflows/build-contract.yml/badge.svg)](https://github.com/asastats/rewards-suite/actions/workflows/build-contract.yml) [![docs](https://app.readthedocs.org/projects/rewards-suite/badge/?version=latest)](https://rewards-suite.readthedocs.io/en/latest/?badge=latest) [![codecov](https://codecov.io/gh/asastats/rewards-suite/graph/badge.svg?token=DQC4SRY8J9)](https://codecov.io/gh/asastats/rewards-suite) ![ansible-lint](https://github.com//asastats/rewards-suite/actions/workflows/ansible-lint.yml/badge.svg) ![molecule](https://github.com/asastats/rewards-suite/actions/workflows/molecule.yml/badge.svg) 

This repository contains the infrastructure code for a user rewards system that incentivizes project contributions.

## How It Works

The website powered by this infrastructure displays historical and recent contributions, hot tasks, contribution guides, and more. To suggest rewards for contributions displayed on the website, community members can use the [Discord Bot](https://github.com/asastats/rewards-suite/tree/main/rewardsweb/rewardsbot) or create comments on social media that will trigger the [powered tracker](https://github.com/asastats/rewards-suite/tree/main/rewardsweb/trackers).

> [!IMPORTANT]
> For the bot to access all channels in the dedicated Discord guilds, an admin must assign it a role with appropriate permissions (the `Verified` role in the case of ASA Stats Discord).

### Environment Variables

Environment variables should not be stored in the repository, so `.env` files must be created based on `.env-example`:

- Website variables are placed in `rewardsweb/.env`
- Discord bot variables are placed in `rewardsweb/rewardsbot/.env`
- Rewards smart contract variables are placed in `rewardsweb/rewards/.env`
- Please check `deploy/.env-example` for deployment variables

> [!NOTE]
> If the `ADMIN_*_MNEMONIC` variable is not set in `rewardsweb/rewards/.env`, the system will treat the logged-in superuser as the admin. You will then need to assign the admin's public address to that superuser.

## Quick Start

Please check the [setup section](https://rewards-suite.readthedocs.io/en/latest/development.html#setup) in the documentation.

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
- [x] Create trackers and related parsers for mentions in social media messages (X and Reddit)
- [x] Enable automatic generation of transparency report snippets based on Mainnet allocations
- [ ] Setup a server and deploy the application
- [ ] Deploy the smart contract on Mainnet
