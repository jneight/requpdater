# coding=utf-8

import argparse
import asyncio
import aiohttp as http
import json
import re
import distutils.version as version_utils


URL = 'http://pypi.python.org/pypi/{0}/json'
PACKAGE_REGEX = '(?P<pkg>[0-9-_A-Za-z]*)(?P<filter>[<>=!]*)(?P<version>[0-9-_A-Za-z.]*)'
regex = re.compile(PACKAGE_REGEX)


@asyncio.coroutine
def check_file(input, output):
    """
        Open the files and creates a task for each line (package),
        after each task is done, the updated package will be added to
        output
    """
    http_session = http.Session()
    fs = []
    with open(input, 'r') as f:
        for line in f:
            print('line {0}'.format(line))
            fs.append(asyncio.Task(check_pkg(line, http_session)))

    with open(output, 'w') as f:
        # this will wait until all tasks are completed
        for future in asyncio.as_completed(fs):
            pkg, versions = yield from future
            if pkg:
                f.write('{0}=={1}\n'.format(pkg, versions[1]))


@asyncio.coroutine
def check_pkg(line_readed, http_session):
    pkg, filtering, version = regex.search(line_readed).groups()
    response = yield from http.request(
        'GET', URL.format(pkg), session=http_session)
    print('response {0}'.format(line_readed))
    body = yield from response.read()
    try:
        body_json = json.loads(body.decode('utf-8', 'replace'))
    except:
        print('Package not found: {0}'.format(line_readed))
        return None, (None, None)
    pkg_info = yield from parse_pkg(
        pkg, filtering, version, body_json['info']['name'],
        body_json['info']['version'])
    return pkg_info


@asyncio.coroutine
def parse_pkg(pkg, filtering, old_version, name, version):
    if filtering:
        if any([not filtering, filtering == '>=' and \
                version_utils.LooseVersion(version) >= \
                version_utils.LooseVersion(old_version),
                filtering == '==' and \
                version_utils.LooseVersion(version) == \
                version_utils.LooseVersion(old_version),
                filtering == '>' and \
                version_utils.LooseVersion(version) > \
                version_utils.LooseVersion(old_version)]):
            return name, (old_version, version)
    return name, (version, version)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-r', '--requirements', help='Requirements file', required=True)
    parser.add_argument('-o', '--output', help='File to write', required=True)
    args = parser.parse_args()
    print('Using file: {0}'.format(args.requirements))

    loop = asyncio.get_event_loop()
    corr = check_file(args.requirements, args.output)
    loop.run_until_complete(corr)
    print('Output writed to: {0}'.format(args.output))

