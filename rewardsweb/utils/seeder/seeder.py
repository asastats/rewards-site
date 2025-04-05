from .cycle_seeder import CycleSeeder
from .contributor_seeder import ContributorSeeder
from .contribution_seeder import ContributionSeeder
from .legacy_contribution_seeder import LegacyContributionSeeder
from .reward_seeder import RewardSeeder

class SeederUtil:
    def __init__(self):
        pass

    def seed_contributions(self, csv_file):
        seeders = [
            CycleSeeder(),
            ContributorSeeder(),
            ContributionSeeder(),
            LegacyContributionSeeder(),
            RewardSeeder(),
        ]