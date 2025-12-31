import json
import requests
import time


class ZSR:
    """
    Class for interacting with ootrandomizer.com to generate seeds and available presets.
    """
    seed_public = 'https://ootrandomizer.com/seed/get?id=%(id)s'
    seed_endpoint = 'https://ootrandomizer.com/api/v2/seed/create'
    status_endpoint = 'https://ootrandomizer.com/api/v2/seed/status'
    details_endpoint = 'https://ootrandomizer.com/api/v2/seed/details'
    password_endpoint = 'https://ootrandomizer.com/api/v2/seed/pw'
    version_endpoint = 'https://ootrandomizer.com/api/version'

    randomizer_branches = {
        'stable': {
            'name': 'Stable (Release)',
            'target_name': 'master',
            'settings_endpoint': 'https://raw.githubusercontent.com/OoTRandomizer/OoT-Randomizer/release/data/presets_default.json'
        },
        'dev': {
            'name': 'Dev (Main)',
            'target_name': 'dev',
            'settings_endpoint': 'https://raw.githubusercontent.com/OoTRandomizer/OoT-Randomizer/Dev/data/presets_default.json'
        },
        'dev-rob': {
            'name': 'Dev-Rob',
            'target_name': 'devrreal',
            'settings_endpoint': 'https://raw.githubusercontent.com/rrealmuto/OoT-Randomizer/Dev-Rob/data/presets_default.json'
        },
        'dev-fenhl': {
            'name': 'Dev-Fenhl',
            'target_name': 'devFenhl',
            'settings_endpoint': 'https://raw.githubusercontent.com/fenhl/OoT-Randomizer/dev-fenhl/data/presets_default.json'
        },
        'dev-enemy-shuffle': {
            'name': 'Dev-Enemy-Shuffle',
            'target_name': 'devEnemyShuffle',
            'settings_endpoint': 'https://raw.githubusercontent.com/rrealmuto/OoT-Randomizer/enemy_shuffle/data/presets_default.json'
        }
    }

    hash_map = {
        'Beans': 'HashBeans',
        'Big Magic': 'HashBigMagic',
        'Bombchu': 'HashBombchu',
        'Boomerang': 'HashBoomerang',
        'Boss Key': 'HashBossKey',
        'Bottled Fish': 'HashBottledFish',
        'Bottled Milk': 'HashBottledMilk',
        'Bow': 'HashBow',
        'Compass': 'HashCompass',
        'Cucco': 'HashCucco',
        'Deku Nut': 'HashDekuNut',
        'Deku Stick': 'HashDekuStick',
        'Fairy Ocarina': 'HashFairyOcarina',
        'Frog': 'HashFrog',
        'Gold Scale': 'HashGoldScale',
        'Heart Container': 'HashHeart',
        'Hover Boots': 'HashHoverBoots',
        'Kokiri Tunic': 'HashKokiriTunic',
        'Lens of Truth': 'HashLensOfTruth',
        'Longshot': 'HashLongshot',
        'Map': 'HashMap',
        'Mask of Truth': 'HashMaskOfTruth',
        'Master Sword': 'HashMasterSword',
        'Megaton Hammer': 'HashHammer',
        'Mirror Shield': 'HashMirrorShield',
        'Mushroom': 'HashMushroom',
        'Saw': 'HashSaw',
        'Silver Gauntlets': 'HashSilvers',
        'Skull Token': 'HashSkullToken',
        'Slingshot': 'HashSlingshot',
        'SOLD OUT': 'HashSoldOut',
        'Stone of Agony': 'HashStoneOfAgony',
    }

    notes_map = {
        'A': 'NoteA',
        'C down':'NoteCdown',
        'C up':'NoteCup',
        'C left':'NoteCleft',
        'C right':'NoteCright',
    }

    def __init__(self, ootr_api_key):
        self.ootr_api_key = ootr_api_key
        self.presets = {}
        self.branch_versions = {}

        for branch in self.randomizer_branches:
            self.load_presets(branch)
            self.get_latest_version(branch)

    def get_latest_version(self, branch):
        """
        Fetch the latest version of the supplied randomzier branch.
        """
        target = self.randomizer_branches[branch]['target_name']
        version_req = requests.get(self.version_endpoint, params={'branch': target}).json()
        latest_version = version_req['currentlyActiveVersion']

        if latest_version != self.branch_versions.get(branch):
            self.branch_versions[branch] = latest_version
            return latest_version, True
        return latest_version, False
                
    def load_presets(self, branch):
        """
        Load and return available seed presets.
        """
        settings = requests.get(self.randomizer_branches[branch]['settings_endpoint']).json()

        self.presets[branch] = {
            min(settings[preset]['aliases'], key=len): {
                'full_name': preset,
                'settings': settings.get(preset),
            }
            for preset in settings if 'aliases' in settings[preset]
        }

    def roll_seed(self, preset, encrypt, branch, password=False):
        """
        Generate a seed and return its public URL.
        """
        dev = branch != 'stable'

        if dev:
            latest_version, changed = self.get_latest_version(branch)
            if changed:
                self.load_presets(branch)
        req_body = json.dumps(self.presets[branch][preset]['settings'])

        params = {
            'key': self.ootr_api_key,
        }
        if encrypt and not dev:
            params['encrypt'] = 'true'
        if encrypt and dev:
            params['locked'] = 'true'
        if password:
            params['passwordLock'] = 'true'
        if dev:
            params['version'] = self.randomizer_branches[branch]['target_name'] + '_' + latest_version
        data = requests.post(self.seed_endpoint, req_body, params=params,
                             headers={'Content-Type': 'application/json'}).json()
        return data['id'], self.seed_public % data

    def get_status(self, seed_id):
        data = requests.get(self.status_endpoint, params={
            'id': seed_id,
            'key': self.ootr_api_key,
        }).json()
        return data['status']

    def get_hash(self, seed_id):
        data = requests.get(self.details_endpoint, params={
            'id': seed_id,
            'key': self.ootr_api_key,
        }).json()
        try:
            settings = json.loads(data.get('settingsLog'))
        except ValueError:
            return None
        return ' '.join(
            self.hash_map.get(item, item)
            for item in settings['file_hash']
        )

    def get_password(self, seed_id, retries=3, delay=2):
        """
        Grab password for seed with active password.

        Tries to retrieve the password a specified number of times,
        with a delay between attempts. Returns None if unsuccessful.
        """
        for attempt in range(retries):
            try:
                data = requests.get(self.password_endpoint, params={
                    'id': seed_id,
                    'key': self.ootr_api_key,
                }, timeout=5)

                data.raise_for_status()

                password_notes = data.json().get('pw')

                return ' '.join(
                    self.notes_map.get(item, item)
                    for item in password_notes
                )
            except (TypeError, ValueError, requests.RequestException):
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    return None
