import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))


import json
import codecs

from utils import FileHelper, common, logger as loggerFactory
from utils.license.oss_license import OpenSourceLicense


class LicenseRepository(object):
    def __init__(self, logger: loggerFactory = None):

        self.__logger = logger if logger is not None else loggerFactory.getLogger(filename="{}.log".format(self.__class__.__name__), log_file_path=common.BATCH_LOG_PATH)
        self.__license_codes = {}
        self.__OSL = OpenSourceLicense()

    @property
    def license_codes(self) -> dict:
        license_codes = {}
        if len(self.__license_codes.items()) == 0:
            with codecs.open("database_license_code.json", "r", "utf-8") as file:
                license_codes = json.load(file)
        
        self.__license_codes = license_codes
        
        return self.__license_codes
        

    def get_license_id(self, license_name, default_license_id=88888):
        license_name = license_name.replace("\"", "'")
        if license_name == 'Apache License V2.0' or license_name == 'Apache License 2.0 (Apache)' or license_name == 'License : Apache License 2.0':
            license_name = 'Apache License 2.0'
        elif license_name == 'GNU Library or Lesser General Public License version 2.0 (LGPLv2)':
            license_name = 'GNU Lesser General Public License v2.1'
        elif license_name == 'GNU General Public License v2 (GPLv2)' or license_name == 'GNU General Public License version 2 (GPLv2)' or license_name == 'GNU General Public License version 2.0 (GPLv2)':
            license_name = 'GNU General Public License v2.0'
        elif license_name == 'GNU GPL v2':
            license_name = 'GNU General Public License v2.0'
        elif license_name == 'GNU General Public License version 3 (GPLv3)' or license_name == 'GNU General Public License v3 (GPLv3)' or license_name == 'GNU General Public License version 3.0 (GPLv3)':
            license_name = 'GNU General Public License v3.0'
        elif license_name == 'GNU GPL v3':
            license_name = 'GPL-3.0'
        elif license_name == 'Boost Software License (BSL1.0)':
            license_name = 'Boost Software License 1.0'
        elif license_name == 'The MIT License (MIT)':
            license_name = 'MIT License'
        elif license_name == 'Microsoft Public License (Ms-PL)' or license_name == 'Microsoft Permissive License (Ms-PL) v1.1':
            license_name = 'Microsoft Public License'
        elif license_name == 'Microsoft Reciprocal License (Ms-RL)':
            license_name = 'Microsoft Reciprocal License'
        elif license_name == 'Common Development and Distribution License (CDDL)':
            license_name = 'Common Development and Distribution License 1.0'
        elif license_name == 'New BSD License (BSD)':
            license_name = 'BSD-3-Clause'
        elif license_name == 'Eclipse Public License (EPL)':
            license_name = 'Eclipse Public License 1.0'
        elif license_name == 'Microsoft Community License (Ms-CL) v1.1':
            license_name = ''  # 누락 된 라이선스
        elif license_name == 'GNU Library General Public License (LGPL)':
            license_name = 'GNU Library General Public License v2'
        elif license_name == 'GNU Lesser General Public License (LGPL)':
            license_name = 'GNU Lesser General Public License v2.1'
        elif license_name == 'Affero General Public License v1.0 only':
            license_name = 'Affero General Public License v1.0'
        elif license_name == 'Mozilla Public License 1.1 (MPL)':
            license_name = 'Mozilla Public License 1.1'
        elif license_name == 'BSD 3-Clause Clear License':
            license_name = 'BSD 3-clause Clear License'
        elif license_name == 'Apache Software License':
            license_name = 'Apache License 1.0'
        elif license_name == 'GNU Lesser General Public License v3 (LGPLv3)' or license_name == 'GNU Library or Lesser General Public License version 3.0 (LGPLv3)':
            license_name = 'GNU Lesser General Public License v3.0'
        elif license_name == 'Eclipse Public License v1.0':
            license_name = 'Eclipse Public License 1.0'
        elif license_name == 'GNU Affero General Public License v3 (AGPLv3)':
            license_name = 'GNU Affero General Public License v3.0'
        elif license_name == 'GNU Lesser General Public License v2.1 (LGPLv2.1)':
            license_name = 'GNU Lesser General Public License v2.1'
        elif license_name == 'Creative Commons Attribution license (CC-BY)' or license_name == 'Creative Commons':
            license_name = 'Creative Commons Attribution 1.0'  # 일단 1.0버젼으로
        elif license_name == 'zlib/libpng License':
            license_name = 'zlib/libpng License with Acknowledgement'
        elif license_name == 'Mozilla Public License (MPL)':
            license_name = 'Mozilla Public License 2.0'
        elif license_name == 'Apple Public Source License':
            license_name = 'Apple Public Source License 1.0'
        elif license_name == 'Creative Commons Attribution-Sharealike license (CC-BY-SA)':
            license_name = 'Creative Commons Attribution Share Alike 1.0'
        elif license_name == 'Creative Commons Attribution ShareAlike License v3.0 (CC-BY-SA 3.0)':
            license_name = 'Creative Commons Attribution Share Alike 3.0'
        elif license_name == 'GNU Free Documentation License':
            license_name = 'GNU Free Documentation License v1.1'
        elif license_name == 'BSD 3-Clause License (aka \'BSD New\' or \'BSD Simplified\' License)':
            license_name = "BSD 2-clause 'Simplified' License"
        elif license_name == 'Common Development and Distribution License':
            license_name = 'Common Development and Distribution License 1.0'
        elif license_name == 'Open Font License 1.1':
            license_name = 'SIL Open Font License 1.1'
        elif license_name == 'BSD 4-Clause \'Original\' or \'Old\' License' or license_name == 'BSD License':
            license_name = "BSD 4-clause 'Original' or 'Old' License"
        elif license_name == 'BSD 2-Clause License (aka FreeBSD License)' or license_name == 'BSD 2-Clause FreeBSD License':
            license_name = 'BSD 2-clause FreeBSD License'
        elif license_name == 'BSD 3-Clause \'New\' or \'Revised\' License':
            license_name = "BSD 3-clause 'New' or 'Revised' License"
        elif license_name == 'Creative Commons Attribution Non Commercial Share Alike 4.0 International':
            license_name = 'Creative Commons Attribution Non Commercial Share Alike 4.0'
        elif license_name == 'BSD 2-Clause \'Simplified\' License' or license_name == 'Simplified BSD License (BSD)':
            license_name = 'BSD 2-clause \'Simplified\' License'
        elif license_name == 'Eclipse Public License 2.0' or license_name == 'Eclipse Public License':
            license_name = 'Eclipse Public License 1.0'  # 일단 1.0버젼으로
        elif license_name == 'Affero GNU Public License':
            license_name = 'Affero General Public License v1.0'  # 일단 1.0버젼으로
        elif license_name == 'Python Software Foundation License' or license_name == 'Python Software Foundation License 2.0':
            license_name = 'Python License 2.0'
        elif license_name == 'Historical Permission Notice and Disclaimer':
            license_name = 'Historic Permission Notice and Disclaimer'
        elif license_name == 'GNU General Public License v3 or later':
            license_name = 'GNU General Public License v3.0'
        elif license_name == 'GNU General Public License v2 or later':
            license_name = 'GNU General Public License v2.0'
        elif license_name == 'GNU Library or Lesser General Public License version 2.0 (LGPLv2)':
            license_name = 'GNU Library General Public License v2'
        elif license_name == 'GNU Lesser General Public License':
            license_name = 'GNU Lesser General Public License v2.1'  # ???
        elif license_name == 'Mozilla Public License 2.0 (MPL-2.0)':
            license_name = 'Mozilla Public License 2.0 (no copyleft exception)'

        # 매칭이 안되는 라이선스
        # other
        # Public Domain
        # Other/Proprietary License
        # MIT/X Consortium License
        # Arphic Public License
        # SIL Open Font License 1.1 with no Reserved Font Name
        # SIL Open Font License 1.1 with Reserved Font Name
        # BSD 3-Clause Open MPI variant
        # Technische Universitaet Berlin License 1.0
        # Eclipse Public License
        # Eclipse Public License 2.0
        # BSD 1-Clause License
        return self.license_codes[license_name] if self.license_codes.get(license_name) else default_license_id

    def find_file_license(self, dir_path, file_path):
        '''
        codebase 아래에 소스 코드 위치
        '''
        filename = "{}/{}".format(dir_path, file_path)
        self.__logger.debug("find_file_license: {}".format(filename))
        license = self.__OSL.find_file_license(filename)
        # 라이선스를 찾지 못한 경우 라이선스 명칭이 파일 내에 포함 되어 있는지 한번더 체크
        if len(license.strip()) == 0 or license.lower() == "unknown":
            license = self.__OSL.check_license_name_in_file(filename)
        return license

