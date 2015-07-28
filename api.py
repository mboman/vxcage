#!/usr/bin/env python
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

# -*- coding: utf-8 -*-

import argparse

from bottle import route, request, response, run
from bottle import HTTPError

from objects import File
from database import Database
from utils import jsonize, store_sample, get_sample_path, get_sample_content

db = Database()

@route("/test", method="GET")
def test():
    return jsonize({"message" : "test"})

@route("/malware/add", method="POST")
def add_malware():
    tags = request.forms.get("tags")
    data = request.files.file
    info = File(path=store_sample(data.file.read()))

    if tags:
        tags = tags.strip()
        if "," in tags:
            tags = tags.split(",")
        else:
            tags = tags.split(" ")
        try:
            tags.append("User:" + request.get('REMOTE_USER'))
        except Exception as e:
            tags.append("User:anonymous")
        tags = ','.join(tags)

    db.add(obj=info, name=data.filename, tags=tags)

    return jsonize({"message" : "added"})

@route("/malware/get/<sha256>", method="GET")
def get_malware(sha256):
    path = get_sample_path(sha256)
    if not path:
        raise HTTPError(404, jsonize({"error": "file_not_found"}))

    response.content_type = "application/octet-stream; charset=UTF-8"
    code, data = get_sample_content(sha256)
    response.content_length = len(data)
    if code == 200:
        return data
    else:
        raise HTTPError(code, data)

@route("/malware/find", method="POST")
def find_malware():
    def details(row):
        tags = []
        for tag in row.tag:
            tags.append(tag.tag)

        entry = {
            "id" : row.id,
            "name" : row.name,
            "type" : row.type,
            "size" : row.size,
            "md5" : row.md5,
            "sha1" : row.sha1,
            "sha256" : row.sha256,
            "sha512" : row.sha512,
            "crc32" : row.crc32,
            "ssdeep": row.ssdeep,
            "created_at": row.created_at.__str__(),
            "tags" : tags
        }

        return entry

    md5 = request.forms.get("md5")
    sha256 = request.forms.get("sha256")
    ssdeep = request.forms.get("ssdeep")
    tag = request.forms.get("tag")
    date = request.forms.get("date")

    if md5:
        row = db.find_md5(md5)
        if row:
            return jsonize(details(row))
        else:
            raise HTTPError(404, "File not found")
    elif sha256:
        row = db.find_sha256(sha256)
        if row:
            return jsonize(details(row))
        else:
            raise HTTPError(404, "File not found")
    else:
        if ssdeep:
            rows = db.find_ssdeep(ssdeep)
        elif tag:
            rows = db.find_tag(tag)
        elif date:
            rows = db.find_date(date)
        else:
            return HTTPError(400, "Invalid search term")

        if not rows:
            return HTTPError(404, "File not found")

        results = []
        for row in rows:
            entry = details(row)
            results.append(entry)

        return jsonize(results)

@route("/tags/list", method="GET")
def list_tags():
    rows = db.list_tags()

    results = []
    for row in rows:
        results.append(row.tag)

    return jsonize(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", help="Host to bind the API server on", default="localhost", action="store", required=False)
    parser.add_argument("-p", "--port", help="Port to bind the API server on", default=8080, action="store", required=False)
    args = parser.parse_args()

    run(host=args.host, port=args.port)
