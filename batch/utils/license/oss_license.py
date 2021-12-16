#-*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import json
import math
import codecs
from collections import deque
import multiprocessing

class VectorCompare:
    def magnitude(self, concordance):
        if type(concordance) != dict:
            raise ValueError('Supplied Argument should be of type dict')
        total = 0
        for word, count in concordance.items():
            total += count ** 2
        return math.sqrt(total)

    def relation(self, concordance1, concordance2):
        if type(concordance1) != dict:
            raise ValueError('Supplied Argument 1 should be of type dict')
        if type(concordance2) != dict:
            raise ValueError('Supplied Argument 2 should be of type dict')
        relevance = 0
        topvalue = 0
        for word, count in concordance1.items():
            if word in concordance2:
                topvalue += count * concordance2[word]

        if (self.magnitude(concordance1) * self.magnitude(concordance2)) != 0:
            return topvalue / (self.magnitude(concordance1) * self.magnitude(concordance2))
        else:
            return 0

    def concordance(self, document):
        con = {}
        for word in document.split(' '):
            if word in con:
                con[word] = con[word] + 1
            else:
                con[word] = 1
        return con


class OpenSourceLicense(object):
    POSSIBLE_LICENSE_FILES = ['license', 'license.txt', 'readme', 'readme.txt', 'copying', 'copying.txt']
    TARGET_EXTENSION = [
        # C
        '.c', '.h',
        # C++
        '.cxx', '.cpp', '.hpp', '.hxx', '.cc',
        # Java
        '.java', 
        # C#
        '.cs',
        # Object-C
        '.m', '.mm', 
        # Perl
        '.perl', '.pl', 
        # PHP
        '.php', '.php3',
        # python
        '.py', '.python',
        # ruby
        '.rails', '.ror', 'ruby', '.rb',
        # Delphi
        '.pas', '.pascal'
        # Javascript
        '.js',  '.javascript', 'jScript',
        # Visual Basic
        '.vb', '.vbnet', '.vbs', '.bas',
        # groovy
        '.groovy',
        # JSP
        '.jsp',
        # ASP
        '.asp', '.asa', '.aspx',
        # GO 
        '.go',
        # Switft
        '.switf',
        # FORTRAN
        '.for',
        # Scala
        '.scala',
        # Lua
        '.lua', 
        # Haskell
        '.hs',
        # Erlang
        '.hrl',
        # COBLOL
        '.cob',
        # ETC
        '.css', '.json', '.asm',  '.bat',  '.cls', '.inc', '.phtml', '.ts']
    IGNORE_DIRECTORY = ['/.git', '/.setting', '/.svn']

    def __init__(self):
        self.module_path = os.path.dirname(__file__)
        self.cpu_count = multiprocessing.cpu_count()
        self.pool = None
        self.vector_compare = VectorCompare()
        self.licenses = self._load_database()
        self.license_codes = self._load_license_code()
        self.license_names = self._load_license_names()
        self.license_queue = deque()

    # https://stackoverflow.com/questions/25382455/python-notimplementederror-pool-objects-cannot-be-passed-between-processes
    '''
    In order to pickle the instance method you're trying to pass to the Pool, 
    Python needs to pickle the entire PageControler object, including its instance variables. 
    One of those instance variables is the Pool object itself, 
    and Pool objects can't be pickled, hence the error. 
    You can work around this by implementing __getstate__ on the object, 
    and using that to remove the pool object from the instance prior to pickling:
    '''
    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['pool']
        return self_dict
    
    def __setstate__(self, state):
        self.__dict__.update(state)

    def _load_database(self):
        with codecs.open(self.module_path+'/database_keywords.json', 'r', 'utf-8') as file:
            database = file.read()

        licenses = json.loads(database)

        for license in licenses:
            license['clean'] = self._clean_text(license['text'])
            license['concordance'] = self.vector_compare.concordance(license['clean'])

        return licenses
    
    def _load_license_code(self):
        with codecs.open(self.module_path+"/database_license_code.json", "r", "utf-8") as file:
            license_codes = json.load(file)
        
        return license_codes

    def _load_license_names(self):
        with codecs.open(self.module_path+"/database_license_names.json", "r", "utf-8") as file:
            license_names = json.load(file)
        
        return license_names
    
    def _clean_text(self, content):
        text = content.lower()
        text = ' '.join(text.split())
        return text
        
    def read_clean_file(self, filename):
        try:
            with codecs.open(filename, 'r', encoding='utf-8', errors='ignore') as fp:
                contents = self._clean_text(fp.read())
        except IOError as e:
            sys.stderr.write("error %d (%s)" % (e.errno, e.strerror))
            contents = ''
        return contents

    def _keyword_guess(self, check_license):
        matching = []
        for license in self.licenses:
            keyword_match = 0
            for keyword in license['keywords']:
                if keyword in check_license: keyword_match += 1
            if len(license['keywords']):
                if keyword_match >= 1:
                    matching.append({
                        'shortname': license['shortname'],
                        'percentage': (float(keyword_match) / float(len(license['keywords'])) * 100)
                    })
        return matching
    
    def _guess_license(self, check_license, filename, root):
        matching = self._keyword_guess(check_license)

        matches = []

        for license in [x for x in self.licenses if x['shortname'] in [y['shortname'] for y in matching]]:
            check_license_concordance = self.vector_compare.concordance(check_license[:len(license['clean'])])

            relation = self.vector_compare.relation(license['concordance'], check_license_concordance)

            if relation >= 0.85:
                matches.append({
                    'relation': relation,
                    'license': license,
                    'root': root,
                    'target_file': filename
                })
        matches = sorted(matches, key=lambda x: -x['relation'])

        return matches

    def guess_license(self, filename, root):
        potential_license = self.read_clean_file(filename)
        guesses = self._guess_license(potential_license, filename, root)

        return guesses

    def find_possible_license_files(self, files):
        possible_files = [x for x in files if x.lower() in OpenSourceLicense.POSSIBLE_LICENSE_FILES and os.path.isfile(x)]

        return possible_files
    
    @staticmethod
    def check_file_extension(filename):
        return len([ext for ext in OpenSourceLicense.TARGET_EXTENSION if filename.endswith(ext)]) >= 1

    def find(self, project_directory):
        self.license_queue.clear()
        result = []
        for root, dirs, files in os.walk(project_directory):

            possible_license_files = self.find_possible_license_files(files)
            
            for possible_file in [root + '/' + x for x in possible_license_files]:
                licenses = self.guess_license(possible_file, root)
                if len(licenses):
                    # for license in licenses:
                    #     license['root'] = root
                    #     license["target_file"] = possible_file # 라이선스가 명시 된 파일 
                    self.license_queue.append(licenses)
            
            if self.license_queue and self.license_queue[-1][0]['root'] not in root:
                self.license_queue.pop()

            if self.license_queue:
                if self.license_queue[-1][0].get("target_file") and self.license_queue[-1][0]['root'] == root:
                    # print(license_queue[-1][0]['target_file'].replace(project_directory, ''), ' > ', license_queue[-1][0]['license']['shortname'])
                    # result.append((
                    #     license_queue[-1][0]['target_file'].replace(project_directory, ''),
                    #     license_queue[-1][0]['license']['shortname']
                    #     ))
                    file_path, file_license = self.license_queue[-1][0]['target_file'].replace(project_directory, ''), self.license_queue[-1][0]['license']['shortname']
                else:
                    # print(root.replace(project_directory, ''), ' > ', license_queue[-1][0]['license']['shortname'])
                    # result.append((
                    #     root.replace(project_directory, ''),
                    #     license_queue[-1][0]['license']['shortname']
                    #     ))
                    file_path, file_license = root.replace(project_directory, ''), self.license_queue[-1][0]['license']['shortname']
            else: 
                # print(root.replace(project_directory, ''))
                file_path, file_license = root.replace(project_directory, ''), "Unknown"

            result.append((
                file_path,
                file_license
            ))
            for f in [root + '/' + x for x in files if OpenSourceLicense.check_file_extension(x)]:
                # 현 디렉토리의 라이선스 설정 
                file_license = self.license_queue[-1][0]['license']['shortname'] if self.license_queue else "Unknown"
                guesses = self.guess_license(f, root)
                if len(guesses) != 0:
                    # 파일의 라이선스 설정
                    file_license = guesses[0]['license']['shortname']
                # print( f.replace(project_directory, ''), ' > ', file_license)
                result.append((
                    f.replace(project_directory, ''),
                    file_license
                ))
        return result
    
    def guess_file(self, file_path, root, file_license='Unknown'):
        licenses = self.guess_license(file_path, root)
        license_id = '88888'
        if len(licenses) != 0:
            # 파일의 라이선스 설정
            file_license = licenses[0]['license']['fullname'] # ['shortname']
            license_id = licenses[0]['license']['license_id'] if licenses[0]['license'].get('license_id') else '99999'
        return {'file_path': file_path, 'license': file_license, 'license_id': license_id}

    def guess_license_file(self, files, root):
        possible_license_files = self.find_possible_license_files(files)
        
        for possible_file in [root + '/' + x for x in possible_license_files]:
            licenses = self.guess_license(possible_file, root)
            if len(licenses):
                # for license in licenses:
                #     license['root'] = root
                #     license["target_file"] = possible_file # 라이선스가 명시 된 파일
                print("test1", licenses) # test
                self.license_queue.append(licenses)
        
        if self.license_queue and self.license_queue[-1][0]['root'] not in root:
            self.license_queue.pop()

        if self.license_queue:
            print("test2", self.license_queue[-1][0]) # test
            if self.license_queue[-1][0].get("target_file") and self.license_queue[-1][0]['root'] == root:
                file_path = self.license_queue[-1][0]['target_file']
            else:
                file_path = root
                
            file_license = self.license_queue[-1][0]['license']['fullname'], # ['shortname']
            license_id = self.license_queue[-1][0]['license']['license_id']
        else: 
            file_path, file_license, license_id = root, None, '88888'
        return file_path, file_license, license_id

    def get_license_id(self, license_name, default_license_id):
        license_name = license_name.replace("\"", "'")
        if license_name == 'Apache License V2.0' or license_name == 'Apache License 2.0 (Apache)' or license_name == 'License : Apache License 2.0': 
            license_name = 'Apache License 2.0'
        elif license_name == 'GNU Library or Lesser General Public License version 2.0 (LGPLv2)': license_name = 'GNU Lesser General Public License v2.1'
        elif license_name == 'GNU General Public License v2 (GPLv2)' or license_name == 'GNU General Public License version 2 (GPLv2)' or license_name == 'GNU General Public License version 2.0 (GPLv2)': 
            license_name = 'GNU General Public License v2.0'
        elif license_name == 'GNU GPL v2': 
            license_name = 'GNU General Public License v2.0'
        elif license_name == 'GNU General Public License version 3 (GPLv3)' or license_name == 'GNU General Public License v3 (GPLv3)' or license_name == 'GNU General Public License version 3.0 (GPLv3)': 
            license_name = 'GNU General Public License v3.0'
        elif license_name == 'GNU GPL v3': license_name = 'GPL-3.0'
        elif license_name == 'Boost Software License (BSL1.0)': license_name = 'Boost Software License 1.0'
        elif license_name == 'The MIT License (MIT)': license_name = 'MIT License'
        elif license_name == 'Microsoft Public License (Ms-PL)' or license_name == 'Microsoft Permissive License (Ms-PL) v1.1': 
            license_name = 'Microsoft Public License'
        elif license_name == 'Microsoft Reciprocal License (Ms-RL)': license_name = 'Microsoft Reciprocal License'
        elif license_name == 'Common Development and Distribution License (CDDL)': license_name = 'Common Development and Distribution License 1.0'
        elif license_name == 'New BSD License (BSD)': license_name = 'BSD-3-Clause'
        elif license_name == 'Eclipse Public License (EPL)': license_name = 'Eclipse Public License 1.0'
        elif license_name == 'Microsoft Community License (Ms-CL) v1.1': license_name = '' # 누락 된 라이선스 
        elif license_name == 'GNU Library General Public License (LGPL)': license_name = 'GNU Library General Public License v2'
        elif license_name == 'GNU Lesser General Public License (LGPL)': license_name = 'GNU Lesser General Public License v2.1'
        elif license_name == 'Affero General Public License v1.0 only': license_name = 'Affero General Public License v1.0'
        elif license_name == 'Mozilla Public License 1.1 (MPL)': license_name = 'Mozilla Public License 1.1'
        elif license_name == 'BSD 3-Clause Clear License': license_name = 'BSD 3-clause Clear License'
        elif license_name == 'Apache Software License': license_name = 'Apache License 1.0'
        elif license_name == 'GNU Lesser General Public License v3 (LGPLv3)' or license_name == 'GNU Library or Lesser General Public License version 3.0 (LGPLv3)': 
            license_name = 'GNU Lesser General Public License v3.0'
        elif license_name == 'Eclipse Public License v1.0': license_name = 'Eclipse Public License 1.0'
        elif license_name == 'GNU Affero General Public License v3 (AGPLv3)': license_name = 'GNU Affero General Public License v3.0'
        elif license_name == 'GNU Lesser General Public License v2.1 (LGPLv2.1)': license_name = 'GNU Lesser General Public License v2.1'
        elif license_name == 'Creative Commons Attribution license (CC-BY)' or license_name == 'Creative Commons': 
            license_name = 'Creative Commons Attribution 1.0' # 일단 1.0버젼으로 
        elif license_name == 'zlib/libpng License': license_name = 'zlib/libpng License with Acknowledgement'
        elif license_name == 'Mozilla Public License (MPL)': license_name = 'Mozilla Public License 2.0'
        elif license_name == 'Apple Public Source License': license_name = 'Apple Public Source License 1.0'
        elif license_name == 'Creative Commons Attribution-Sharealike license (CC-BY-SA)': license_name = 'Creative Commons Attribution Share Alike 1.0'
        elif license_name == 'Creative Commons Attribution ShareAlike License v3.0 (CC-BY-SA 3.0)': license_name = 'Creative Commons Attribution Share Alike 3.0'
        elif license_name == 'GNU Free Documentation License': license_name = 'GNU Free Documentation License v1.1'
        elif license_name == 'BSD 3-Clause License (aka \'BSD New\' or \'BSD Simplified\' License)': license_name = "BSD 2-clause 'Simplified' License"
        elif license_name == 'Common Development and Distribution License': license_name = 'Common Development and Distribution License 1.0'
        elif license_name == 'Open Font License 1.1': license_name = 'SIL Open Font License 1.1'
        elif license_name == 'BSD 4-Clause \'Original\' or \'Old\' License' or license_name == 'BSD License': 
            license_name = "BSD 4-clause 'Original' or 'Old' License"
        elif license_name == 'BSD 2-Clause License (aka FreeBSD License)' or license_name == 'BSD 2-Clause FreeBSD License': 
            license_name = 'BSD 2-clause FreeBSD License'
        elif license_name == 'BSD 3-Clause \'New\' or \'Revised\' License': license_name = "BSD 3-clause 'New' or 'Revised' License"
        elif license_name == 'Creative Commons Attribution Non Commercial Share Alike 4.0 International': license_name = 'Creative Commons Attribution Non Commercial Share Alike 4.0'
        elif license_name == 'BSD 2-Clause \'Simplified\' License' or license_name == 'Simplified BSD License (BSD)': 
            license_name = 'BSD 2-clause \'Simplified\' License'
        elif license_name == 'Eclipse Public License 2.0' or license_name == 'Eclipse Public License': 
            license_name = 'Eclipse Public License 1.0' # 일단 1.0버젼으로 
        elif license_name == 'Affero GNU Public License': license_name = 'Affero General Public License v1.0' # 일단 1.0버젼으로
        elif license_name == 'Python Software Foundation License' or license_name == 'Python Software Foundation License 2.0': 
            license_name = 'Python License 2.0'
        elif license_name == 'Historical Permission Notice and Disclaimer': license_name = 'Historic Permission Notice and Disclaimer'
        elif license_name == 'GNU General Public License v3 or later': license_name = 'GNU General Public License v3.0'
        elif license_name == 'GNU General Public License v2 or later': license_name = 'GNU General Public License v2.0'
        elif license_name == 'GNU Library or Lesser General Public License version 2.0 (LGPLv2)': license_name = 'GNU Library General Public License v2'
        elif license_name == 'GNU Lesser General Public License': license_name = 'GNU Lesser General Public License v2.1' ### ??? 
        elif license_name == 'Mozilla Public License 2.0 (MPL-2.0)': license_name = 'Mozilla Public License 2.0 (no copyleft exception)'
        
        return self.license_codes[license_name] if self.license_codes.get(license_name) else default_license_id

    def is_ignore_directory(self, target_directory):
        '''
        제외 되어야 할 디렉토리 체크 
        '''
        check_ignore_directory = [(target_directory.find(x) > -1) for x in self.IGNORE_DIRECTORY]
        if any(check_ignore_directory):
            return True
        else:
            return False

    def find_iter(self, project_directory, project_license="Unknown"):
        self.license_queue.clear()

        for root, dirs, files in os.walk(project_directory):
            if self.is_ignore_directory(root): continue

            file_path, file_license, license_id = self.guess_license_file(files, root)
            if file_license is None:
                file_license = project_license
                # license_id = self.license_codes[file_license.replace("\"", "'")] if self.license_codes.get(file_license.replace("\"", "'")) else license_id
                license_id = self.get_license_id(file_license, license_id) 
            elif self.license_queue.empty():
                # 프로젝트 테이블의 라이선스를 수정해야 한다.
                project_license = file_license
                pass

            yield ( file_path.replace(project_directory, '').encode('utf-8', 'replace').decode(), file_license, license_id )

            for f in [root + '/' + x.encode('utf-8', 'replace').decode() for x in files if OpenSourceLicense.check_file_extension(x)]:
                # 파일에 대해서만 라이선스 조사
                if os.path.isfile(f):  
                    # 현 디렉토리의 라이선스를 파라미터로 전달 
                    file_license = self.guess_file(
                        f, 
                        root, 
                        self.license_queue[-1][0]['license']['shortname'] if self.license_queue else project_license
                        )
                    file_license_id = file_license['license_id'] if file_license['license_id'] != '88888' and file_license['license_id'] != '99999' else license_id 
                    yield ( f.replace(project_directory, '').encode('utf-8', 'replace').decode(), file_license['license'], file_license_id  )
    
    def check_license_name_in_file(self, filename):
        potential_license = self.read_clean_file(filename)
        matches = []
        for license in self.license_names:
            if license.lower() in potential_license: 
                matches.append(license)
        matches = sorted(matches, key=lambda x: -len(x))
        return matches[0] if len(matches) > 0 else 'UnKnown'
    
    def find_file_license(self, filename):
        file_license = self.guess_file(filename, "/")
        
        return file_license['license']