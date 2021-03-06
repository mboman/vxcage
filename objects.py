# Copyright (c) 2012, Claudio "nex" Guarnieri
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import hashlib
import binascii
import ConfigParser

from aws import AWSStorage

try:
    import magic
except ImportError:
    pass

try:
    import pydeep

    HAVE_SSDEEP = True
except ImportError:
    HAVE_SSDEEP = False


class Dictionary(dict):
    def __getattr__(self, key):
        return self.get(key, None)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class File:
    def __init__(self, path=None, data=None):
        self.path = path
        self.s3key = None

        if path:
            if Config().api.use_aws:
                self.s3key = AWSStorage.get_key()
                self.s3key.name = self.path
                self.data = self.s3key.get_contents_as_string()
            else:
                self.data = open(self.path, "rb").read()
        else:
            self.data = data

    def get_name(self):
        name = os.path.basename(self.path)
        return name

    def get_data(self):
        return self.data

    def get_size(self):
        if Config().api.use_aws:
            return self.s3key.size
        else:
            return os.path.getsize(self.path)

    def get_crc32(self):
        res = ''
        crc = binascii.crc32(self.data)
        for i in range(4):
            t = crc & 0xFF
            crc >>= 8
            res = '%02X%s' % (t, res)
        return res

    def get_md5(self):
        return hashlib.md5(self.data).hexdigest()

    def get_sha1(self):
        return hashlib.sha1(self.data).hexdigest()

    def get_sha256(self):
        return hashlib.sha256(self.data).hexdigest()

    def get_sha512(self):
        return hashlib.sha512(self.data).hexdigest()

    def get_ssdeep(self):
        if not HAVE_SSDEEP:
            return None

        try:
            if Config().api.use_aws:
                return pydeep.hash_buffer(self.data)
            else:
                return pydeep.hash_file(self.path)
        except Exception:
            return None

    def get_type(self):
        try:
            ms = magic.open(magic.MAGIC_NONE)
            ms.load()
            if not self.path or Config().viper.use_aws:
                file_type = ms.buffer(self.data)
            else:
                file_type = ms.file(self.path)
        except:
            try:
                if not self.path or Config().viper.use_aws:
                    file_type = magic.from_buffer(self.data)
                else:
                    file_type = magic.from_file(self.path)
            except:
                try:
                    import subprocess
                    if not self.path or Config().viper.use_aws:
                        tmp_file_path = tempfile.NamedTemporaryFile(mode='w+b')
                        tmp_file_path.write(self.data)
                        tmp_file_path.flush()
                        file_process = subprocess.Popen(['file', '-b', tmp_file_path], stdout=subprocess.PIPE)
                        file_type = file_process.stdout.read().strip()
                        tmp_file_path.close()
                    else:
                        file_process = subprocess.Popen(['file', '-b', self.path], stdout=subprocess.PIPE)
                        file_type = file_process.stdout.read().strip()
                except:
                    return None

        return file_type


class Config:
    def __init__(self, cfg="api.conf"):
        config = ConfigParser.ConfigParser()
        config.read(cfg)

        for section in config.sections():
            setattr(self, section, Dictionary())
            for name, raw_value in config.items(section):
                try:
                    value = config.getboolean(section, name)
                except ValueError:
                    try:
                        value = config.getint(section, name)
                    except ValueError:
                        value = config.get(section, name)

                setattr(getattr(self, section), name, value)

    def get(self, section):
        try:
            return getattr(self, section)
        except AttributeError as e:
            return None
