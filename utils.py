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
import json

from objects import File, Config
from aws import AWSStorage


def jsonize(data):
    return json.dumps(data, sort_keys=False, indent=4)


def store_sample(data):
    sha256 = File(data=data).get_sha256()

    folder = os.path.join(Config().api.repository, sha256[0], sha256[1], sha256[2], sha256[3])
    path = os.path.join(folder, sha256)

    if Config().api.use_aws:
        s3key = AWSStorage().get_key()
        s3key.name = path
        if not s3key.exists():
            s3key.set_contents_from_string(data)
    else:
        if not os.path.exists(folder):
            os.makedirs(folder, 0750)

        if not os.path.exists(path):
            sample = open(path, "wb")
            sample.write(data)
            sample.close()

    return path


def get_sample_path(sha256):
    path = os.path.join(Config().api.repository, sha256[0], sha256[1], sha256[2], sha256[3], sha256)
    if Config().api.use_aws:
        s3key = AWSStorage.get_key()
        s3key.name = path
        if not s3key.exists():
            return None
    else:
        if not os.path.exists(path):
            return None

    return path


def get_sample_content(sha256):
    path = get_sample_path(sha256)
    if Config().api.use_aws:
        s3key = AWSStorage.get_key()
        s3key.name = path
        if s3key.storage_class == 'GLACIER':
            s3key.restore(15)
            return (503, jsonize({'error': 'sample_not_online'}))
        else:
            return (200, s3key.get_contents_as_string())
    else:
        return open(path, "rb").read()
