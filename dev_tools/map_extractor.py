import os
import re

import numpy as np

from dev_tools.slpp import slpp
from module.base.utils import location2node
from module.map.map_base import camera_2d, camera_spawn_point

"""
This an auto-tool to extract map files used in Alas.
"""

DIC_SIREN_NAME_CHI_TO_ENG = {
    # Siren Winter's Crown, Fallen Wings
    'sairenquzhu': 'DD',
    'sairenqingxun': 'CL',
    'sairenzhongxun': 'CA',
    'sairenzhanlie': 'BB',
    'sairenhangmu': 'CV',
    'sairenqianting': 'SS',

    # Siren cyan
    'sairenquzhu_i': 'DD',
    'sairenqingxun_i': 'CL',
    'sairenzhongxun_i': 'CA',
    'sairenzhanlie_i': 'BB',
    'sairenhangmu_i': 'CV',
    'sairenqianting_i': 'SS',

    # Siren red
    'sairenquzhu_M': 'DD',
    'sairenqingxun_M': 'CL',
    'sairenzhongxun_M': 'CAred',
    'sairenzhanlie_M': 'BB',
    'sairenhangmu_M': 'CV',
    'sairenqianting_M': 'SS',

    # Scherzo of Iron and Blood
    'aruituosha': 'Arethusa',
    'xiefeierde': 'Sheffield',
    'duosaitejun': 'Dorsetshire',
    'shengwang': 'Renown',
    'weiershiqinwang': 'PrinceOfWales',

    # Universe in Unison
    'edu_idol': 'LeMalinIdol',
    'daiduo_idol': 'DidoIdol',
    'daqinghuayu_idol': 'AlbacoreIdol',
    'baerdimo_idol': 'BaltimoreIdol',
    'kelifulan_idol': 'ClevelandIdol',
    'xipeier_idol': 'HipperIdol',
    'sipeibojue_5': 'SpeeIdol',
    'luoen_idol': 'RoonIdol',
    'guanghui_idol': 'IllustriousIdol',

    # Vacation Lane
    'maliluosi_doa': 'MarieRoseDOA',
    'haixiao_doa': 'MisakiDOA',
    'xia_doa': 'KasumiDOA',
    'zhixiao_doa': 'NagisaDOA',

    # The Enigma and the Shark
    'nvjiang': 'Amazon',
}


def load_lua(folder, file, prefix):
    with open(os.path.join(folder, file), 'r', encoding='utf-8') as f:
        text = f.read()
    print(f'Loading {file}')
    result = slpp.decode(text[prefix:])
    print(f'{len(result.keys())} items loaded')
    return result


class MapData:
    dic_grid_info = {
        0: '--',
        1: 'SP',
        2: 'MM',
        3: 'MA',
        4: 'Me',  # This grid 100% spawn enemy?
        6: 'ME',
        8: 'MB',
        12: 'MS',
        16: '__'
    }

    def __init__(self, data, data_loop):
        self.data = data
        self.data_loop = data_loop
        self.chapter_name = data['chapter_name'].replace('–', '-')
        self.name = data['name']
        self.profiles = data['profiles']
        self.map_id = data['id']
        try:
            battle_count = max(data['boss_refresh'], max(data['enemy_refresh'].keys()))
        except ValueError:
            battle_count = 0
        self.spawn_data = [{'battle': index} for index in range(battle_count + 1)]
        try:
            # spawn_data
            for index, count in data['enemy_refresh'].items():
                if count:
                    spawn = self.spawn_data[index]
                    spawn['enemy'] = spawn.get('enemy', 0) + count
            if ''.join([str(item) for item in data['elite_refresh'].values()]) != '100':  # Some data is incorrect
                for index, count in data['elite_refresh'].items():
                    if count:
                        spawn = self.spawn_data[index]
                        spawn['enemy'] = spawn.get('enemy', 0) + count
            for index, count in data['ai_refresh'].items():
                if count:
                    spawn = self.spawn_data[index]
                    spawn['siren'] = spawn.get('siren', 0) + count
            for index, count in data['box_refresh'].items():
                if count:
                    spawn = self.spawn_data[index]
                    spawn['mystery'] = spawn.get('mystery', 0) + count
            try:
                self.spawn_data[data['boss_refresh']]['boss'] = 1
            except IndexError:
                pass

            # map_data
            # {0: {0: 6, 1: 8, 2: False, 3: 0}, ...}
            self.map_data = self.parse_map_data(data['grids'])
            self.shape = tuple(np.max(list(self.map_data.keys()), axis=0))
            if self.data_loop is not None:
                self.map_data_loop = self.parse_map_data(data_loop['grids'])
                if all([d1 == d2 for d1, d2 in zip(self.map_data.values(), self.map_data_loop.values())]):
                    self.map_data_loop = None
            else:
                self.map_data_loop = None

            # portal
            self.portal = []
            if self.map_id in MAP_EVENT_LIST:
                for event_id in MAP_EVENT_LIST[self.map_id]['event_list'].values():
                    event = MAP_EVENT_TEMPLATE[event_id]
                    for effect in event['effect'].values():
                        if effect[0] == 'jump':
                            address = event['address']
                            address = location2node((address[1], address[0]))
                            target = location2node((effect[2], effect[1]))
                            self.portal.append((address, target))

            # land_based
            # land_based = {{6, 7, 1}, ...}
            # Format: {y, x, rotation}
            land_based_rotation_dict = {1: 'up', 2: 'down', 3: 'left', 4: 'right'}
            self.land_based = []
            for lb in data['land_based'].values():
                y, x, r = lb.values()
                self.land_based.append([location2node((x, y)), land_based_rotation_dict[r]])

            # config
            self.MAP_SIREN_TEMPLATE = []
            self.MOVABLE_ENEMY_TURN = set()
            for siren_id in data['ai_expedition_list'].values():
                if siren_id == 1:
                    continue
                exped_data = EXPECTATION_DATA[siren_id]
                name = exped_data['icon']
                name = DIC_SIREN_NAME_CHI_TO_ENG.get(name, name)
                if name not in self.MAP_SIREN_TEMPLATE:
                    self.MAP_SIREN_TEMPLATE.append(name)
                self.MOVABLE_ENEMY_TURN.add(int(exped_data['ai_mov']))
            self.MAP_HAS_MOVABLE_ENEMY = bool(len(self.MOVABLE_ENEMY_TURN))
            self.MAP_HAS_MAP_STORY = len(data['story_refresh_boss']) > 0
            self.MAP_HAS_FLEET_STEP = bool(data['is_limit_move'])
            self.MAP_HAS_AMBUSH = bool(data['is_ambush']) or bool(data['is_air_attack'])
            self.MAP_HAS_PORTAL = bool(len(self.portal))
            self.MAP_HAS_LAND_BASED = bool(len(self.land_based))
            for n in range(1, 4):
                self.__setattr__(f'STAR_REQUIRE_{n}', data[f'star_require_{n}'])
        except Exception as e:
            for k, v in data.items():
                print(f'{k} = {v}')
            raise e

    def __str__(self):
        return f'{self.map_id} {self.chapter_name} {self.name}'

    __repr__ = __str__

    def parse_map_data(self, grids):
        map_data = {}
        offset_y = min([grid[0] for grid in grids.values()])
        offset_x = min([grid[1] for grid in grids.values()])
        for grid in grids.values():
            loca = (grid[1] - offset_x, grid[0] - offset_y)
            if not grid[2]:
                info = '++'
            else:
                info = self.dic_grid_info.get(grid[3], '??')
            if info == '??':
                print(f'Unknown grid info. grid={location2node(loca)}, info={grid[3]}')
            map_data[loca] = info

        return map_data

    def map_file_name(self):
        name = self.chapter_name.replace('-', '_').lower()
        if name[0].isdigit():
            name = f'campaign_{name}'
        return name + '.py'

    def get_file_lines(self):
        """
        Returns:
            list(str): Python code in map file.
        """
        if IS_WAR_ARCHIVES:
            base_import = 'from ..campaign_war_archives.campaign_base import CampaignBase'
        else:
            base_import = 'from module.campaign.campaign_base import CampaignBase'

        header = f"""
            {base_import}
            from module.map.map_base import CampaignMap
            from module.map.map_grids import SelectedGrids, RoadGrids
            from module.logger import logger
        """
        lines = []

        # Import
        for head in header.strip().split('\n'):
            lines.append(head.strip())
        if self.chapter_name[-1].isdigit():
            chap, stage = self.chapter_name[:-1], self.chapter_name[-1]
            if stage != '1':
                lines.append(f'from .{chap.lower()}1 import Config as ConfigBase')
        lines.append('')

        # Map
        lines.append(f'MAP = CampaignMap(\'{self.chapter_name}\')')
        lines.append(f'MAP.shape = \'{location2node(self.shape)}\'')
        camera_data = camera_2d(self.shape, sight=(-3, -1, 3, 2))
        lines.append(
            f'MAP.camera_data = {[location2node(loca) for loca in camera_data]}')
        camera_sp = camera_spawn_point(camera_data, sp_list=[k for k, v in self.map_data.items() if v == 'SP'])
        lines.append(f'MAP.camera_data_spawn_point = {[location2node(loca) for loca in camera_sp]}')
        if self.MAP_HAS_PORTAL:
            lines.append(f'MAP.portal_data = {self.portal}')
        lines.append('MAP.map_data = \"\"\"')
        for y in range(self.shape[1] + 1):
            lines.append('    ' + ' '.join([self.map_data[(x, y)] for x in range(self.shape[0] + 1)]))
        lines.append('\"\"\"')
        if self.map_data_loop is not None:
            lines.append('MAP.map_data_loop = \"\"\"')
            for y in range(self.shape[1] + 1):
                lines.append('    ' + ' '.join([self.map_data_loop[(x, y)] for x in range(self.shape[0] + 1)]))
            lines.append('\"\"\"')
        lines.append('MAP.weight_data = \"\"\"')
        for y in range(self.shape[1] + 1):
            lines.append('    ' + ' '.join(['50'] * (self.shape[0] + 1)))
        lines.append('\"\"\"')
        if self.MAP_HAS_LAND_BASED:
            lines.append(f'MAP.land_based_data = {self.land_based}')
        lines.append('MAP.spawn_data = [')
        for battle in self.spawn_data:
            lines.append('    ' + str(battle) + ',')
        lines.append(']')
        for y in range(self.shape[1] + 1):
            lines.append(', '.join([location2node((x, y)) for x in range(self.shape[0] + 1)]) + ', \\')
        lines.append('    = MAP.flatten()')
        lines.append('')
        lines.append('')

        # Config
        if self.chapter_name[-1].isdigit():
            chap, stage = self.chapter_name[:-1], self.chapter_name[-1]
            if stage != '1':
                lines.append('class Config(ConfigBase):')
            else:
                lines.append('class Config:')
        else:
            lines.append('class Config:')
        lines.append('    # ===== Start of generated config =====')
        if len(self.MAP_SIREN_TEMPLATE):
            lines.append(f'    MAP_SIREN_TEMPLATE = {self.MAP_SIREN_TEMPLATE}')
            lines.append(f'    MOVABLE_ENEMY_TURN = {tuple(self.MOVABLE_ENEMY_TURN)}')
            lines.append(f'    MAP_HAS_SIREN = True')
            lines.append(f'    MAP_HAS_MOVABLE_ENEMY = {self.MAP_HAS_MOVABLE_ENEMY}')
        lines.append(f'    MAP_HAS_MAP_STORY = {self.MAP_HAS_MAP_STORY}')
        lines.append(f'    MAP_HAS_FLEET_STEP = {self.MAP_HAS_FLEET_STEP}')
        lines.append(f'    MAP_HAS_AMBUSH = {self.MAP_HAS_AMBUSH}')
        if self.MAP_HAS_PORTAL:
            lines.append(f'    MAP_HAS_PORTAL = {self.MAP_HAS_PORTAL}')
        if self.MAP_HAS_LAND_BASED:
            lines.append(f'    MAP_HAS_LAND_BASED = {self.MAP_HAS_LAND_BASED}')
        for n in range(1, 4):
            if not self.__getattribute__(f'STAR_REQUIRE_{n}'):
                lines.append(f'    STAR_REQUIRE_{n} = 0')
        lines.append('    # ===== End of generated config =====')
        lines.append('')
        lines.append('')

        # Campaign
        lines.append('class Campaign(CampaignBase):')
        lines.append('    MAP = MAP')
        lines.append('')
        lines.append('    def battle_0(self):')
        if len(self.MAP_SIREN_TEMPLATE):
            lines.append('        if self.clear_siren():')
            lines.append('            return True')
            lines.append('')
        lines.append('        return self.battle_default()')
        lines.append('')
        lines.append(f'    def battle_{self.data["boss_refresh"]}(self):')
        if self.data["boss_refresh"] >= 5:
            lines.append('        return self.fleet_boss.clear_boss()')
        else:
            lines.append('        return self.clear_boss()')

        return lines

    def write(self, path):
        file = os.path.join(path, self.map_file_name())
        if os.path.exists(file):
            if OVERWRITE:
                print(f'Delete file: {file}')
                os.remove(file)
            else:
                print(f'File exists: {file}')
                return False
        print(f'Extract: {file}')
        with open(file, 'w') as f:
            for text in self.get_file_lines():
                f.write(text + '\n')


class ChapterTemplate:
    def __init__(self):
        pass

    def get_chapter_by_name(self, name, select=False):
        """
        11004 (map id) --> 10-4 Hard
        ↑-- ↑
        | | +-- stage index
        | +---- chapter index
        +------ 1 for hard, 0 for normal

        1140017 (map id) --> Iris of Light and Dark D2
        ---  ↑↑
         ↑   |+-- stage index
         |   +--- chapter index
         +------- event index, >=210 for war achieve

        Args:
            name (str, int): A keyword from chapter name, such as '短兵相接', '正义的怒吼'
                Or map_id such as 702, 1140017
            select (bool): False means only extract this map, True means all maps from this event

        Returns:
            list(MapData):
        """
        print('<<< SEARCH MAP >>>')
        name = name.strip()
        name = int(name) if name.isdigit() else name
        print(f'Searching: {name}')
        if isinstance(name, str):
            maps = []
            for map_id, data in DATA.items():
                if not isinstance(map_id, int) or data['chapter_name'] == 'EXTRA':
                    continue
                if not re.search(name, data['name']):
                    continue
                data = MapData(data, DATA_LOOP.get(map_id, None))
                print(f'Found map: {data}')
                maps.append(data)
        else:
            data = MapData(DATA[name], DATA_LOOP.get(name, None))
            print(f'Found map: {data}')
            maps = [data]

        if not len(maps):
            print('No maps found')
            return []
        print('')

        print('<<< SELECT MAP >>>')

        def get_event_id(map_id):
            return (map_id - 2100000) // 20 + 21000 if map_id // 10000 == 210 else map_id // 10000

        if select:
            event_id = get_event_id(maps[0].map_id)
            new = []
            for map_id, data in DATA.items():
                if not isinstance(map_id, int) or data['chapter_name'] == 'EXTRA':
                    continue
                if get_event_id(data['id']) == event_id:
                    data = MapData(data, DATA_LOOP.get(map_id, None))
                    print(f'Selected: {data}')
                    new.append(data)
            maps = new
        else:
            maps = maps[:1]
            print(f'Selected: {maps[0]}')

        print('')
        return maps

    def extract(self, maps, folder):
        """
        Args:
            maps (list[MapData]):
            folder (str):
        """
        print('<<< CONFIRM >>>')
        print('Please confirm selected the correct maps before extracting.\n'
              'Input any key and press ENTER to continue')
        input()

        if not os.path.exists(folder):
            os.mkdir(folder)
        for data in maps:
            data.write(folder)


"""
This an auto-tool to extract map files used in Alas.

Git clone https://github.com/Dimbreath/AzurLaneData, to get the decrypted scripts.
Arguments:
    FILE:            Folder contains `chapter_template.lua` and `expedition_data_template.lua`,
                     Such as '<your_folder>/<server>/sharecfg'
    FOLDER:          Folder to save, './campaign/test'
    KEYWORD:         A keyword in map name, such as '短兵相接' (7-2, zh-CN), 'Counterattack!' (3-4, en-US)
                     Or map id, such as 702 (7-2), 1140017 (Iris of Light and Dark D2)
    SELECT:          True if select all maps in the same event
                     False if extract this map only
    OVERWRITE:       If overwrite existing files
    IS_WAR_ARCHIVES: True if retrieved map is to be
                     adapted for war_archives usage
"""
FILE = ''
FOLDER = './campaign/test'
KEYWORD = ''
SELECT = False
OVERWRITE = True
IS_WAR_ARCHIVES = False

DATA = load_lua(FILE, 'chapter_template.lua', prefix=36)
DATA_LOOP = load_lua(FILE, 'chapter_template_loop.lua', prefix=41)
MAP_EVENT_LIST = load_lua(FILE, 'map_event_list.lua', prefix=34)
MAP_EVENT_TEMPLATE = load_lua(FILE, 'map_event_template.lua', prefix=38)
EXPECTATION_DATA = load_lua(FILE, 'expedition_data_template.lua', prefix=43)

ct = ChapterTemplate()
ct.extract(ct.get_chapter_by_name(KEYWORD, select=SELECT), folder=FOLDER)
