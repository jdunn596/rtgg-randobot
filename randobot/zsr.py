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
    settings_endpoints = [
        'https://raw.githubusercontent.com/OoTRandomizer/OoT-Randomizer/release/data/presets_default.json',
        'https://raw.githubusercontent.com/OoTRandomizer/OoT-Randomizer/Dev/data/presets_default.json',
        'https://raw.githubusercontent.com/rrealmuto/OoT-Randomizer/Dev-Rob/data/presets_default.json',
        'https://raw.githubusercontent.com/fenhl/OoT-Randomizer/dev-fenhl/data/presets_default.json',
        'https://raw.githubusercontent.com/rrealmuto/OoT-Randomizer/enemy_shuffle/data/presets_default.json'
    ]

    valid_version_args = ['stable', 'dev', 'dev-rob', 'dev-fenhl', 'dev-enemy-shuffle']
    version_names = ['Stable (Release)', 'Dev (Main)', 'Dev-Rob', 'Dev-Fenhl', 'Dev-Enemy-Shuffle']
    ootr_version_names = ['master', 'dev', 'devrreal', 'devFenhl', 'devEnemyShuffle']

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
        self.version_map = {}
        self.build_version_map()

    def build_version_map(self):
        for i, rtgg_arg in enumerate(self.valid_version_args):
            self.version_map[rtgg_arg] = Branch(
                rtgg_arg = rtgg_arg,
                name=self.version_names[i],
                ootr_name=self.ootr_version_names[i],
                version=self.get_latest_version(self.ootr_version_names[i]),
                settings_endpoint=self.settings_endpoints[i]
            )

    def get_latest_version(self, ootr_name):
        """
        Fetch the latest version of the supplied randomzier branch.
        """
        version_req = requests.get(self.version_endpoint, params={'branch': ootr_name}).json()
        latest_version = version_req['currentlyActiveVersion']
        return latest_version

    def roll_seed(self, preset, encrypt, branch, password=False):
        """
        Generate a seed and return its public URL.
        """
        dev = branch.rtgg_arg != 'stable'

        if dev:
            latest_version = self.get_latest_version(branch.ootr_name)
            if latest_version != branch.version:
                branch.update_version(latest_version)
                branch.load_presets()
        req_body = json.dumps(branch.presets[preset]['settings'])

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
            params['version'] = branch.ootr_name + '_' + branch.version
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


class Branch:
    def __init__(self, rtgg_arg, name, ootr_name, version, settings_endpoint):
        self.rtgg_arg = rtgg_arg
        self.name = name
        self.ootr_name = ootr_name
        self.version = version
        self.settings_endpoint = settings_endpoint
        self.presets = self.load_presets()

    def load_presets(self):
        settings = requests.get(self.settings_endpoint).json()

        return {
            min(settings[preset]['aliases'], key=len): {
                'full_name': preset,
                'settings': settings.get(preset),
            }
            for preset in settings if 'aliases' in settings[preset]
        }
    
    def update_version(self, version):
        self.version = version
