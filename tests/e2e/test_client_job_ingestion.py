# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from mock import MagicMock
import json

from treeherder.client.thclient import client

from treeherder.etl.oauth_utils import OAuthCredentials
from treeherder.log_parser.parsers import StepParser
from treeherder.model.derived import JobsModel, ArtifactsModel
from treeherder.model import error_summary


@pytest.fixture
def text_log_summary_blob():
    return {
        "header": {},
        "step_data": {
            "all_errors": [
                {"line": "12:34:13     INFO -  Assertion failure: addr % CellSize == 0, at ../../../js/src/gc/Heap.h:1041", "linenumber": 61918},
                {"line": "12:34:24  WARNING -  TEST-UNEXPECTED-FAIL | file:///builds/slave/talos-slave/test/build/tests/jsreftest/tests/jsreftest.html?test=ecma_5/JSON/parse-array-gc.js | Exited with code 1 during test run", "linenumber": 61919}, {"line": "12:34:37  WARNING -  PROCESS-CRASH | file:///builds/slave/talos-slave/test/build/tests/jsreftest/tests/jsreftest.html?test=ecma_5/JSON/parse-array-gc.js | application crashed [@ js::gc::Cell::tenuredZone() const]", "linenumber": 61922},
                {"line": "12:34:38    ERROR - Return code: 256", "linenumber": 64435}
            ],
            "steps": [
                {"name": "Clone gecko tc-vcs "},
                {"name": "Build ./build-b2g-desktop.sh /home/worker/workspace"}
            ],
            "errors_truncated": False
        },
        "logurl": "https://queue.taskcluster.net/v1/task/nhxC4hC3RE6LSVWTZT4rag/runs/0/artifacts/public/logs/live_backing.log"
    }


def do_post_collection(project, collection):
    # assume if there were no exceptions we're ok
    cli = client.TreeherderClient(protocol='http', host='localhost')
    credentials = OAuthCredentials.get_credentials(project)
    cli.post_collection(project, credentials['consumer_key'],
                        credentials['consumer_secret'], collection)


def check_artifacts(test_project,
                    job_guid,
                    parse_status,
                    num_artifacts,
                    exp_artifact_names=None,
                    exp_error_summary=None):

    with JobsModel(test_project) as jobs_model:
        jobs_model.process_objects(10)
        job_id = [x['id'] for x in jobs_model.get_job_list(0, 20)
                  if x['job_guid'] == job_guid][0]
        job_log_list = jobs_model.get_job_log_url_list([job_id])

        print job_log_list
        assert len(job_log_list) >= 1
        assert job_log_list[0]['parse_status'] == parse_status

    with ArtifactsModel(test_project) as artifacts_model:
        artifacts = artifacts_model.get_job_artifact_list(0, 10, conditions={
            'job_id': {('=', job_id)}
        })

        assert len(artifacts) == num_artifacts

        if exp_artifact_names:
            artifact_names = {x['name'] for x in artifacts}
            assert set(artifact_names) == exp_artifact_names

        if exp_error_summary:
            act_bs_obj = [x['blob'] for x in artifacts if x['name'] == 'Bug suggestions'][0]
            assert exp_error_summary == act_bs_obj


def test_post_job_with_parsed_log(test_project, result_set_stored,
                                  mock_post_collection,
                                  monkeypatch,
                                  ):
    """
    test submitting a job with a pre-parsed log gets job_log_url
    parse_status of "parsed" and does not parse, even though no text_log_summary
    exists.

    This is for the case where they may want to submit it at a later time.
    """

    mock_parse = MagicMock(name="parse_line")
    monkeypatch.setattr(StepParser, 'parse_line', mock_parse)

    tjc = client.TreeherderJobCollection()
    job_guid = 'd22c74d4aa6d2a1dcba96d95dccbd5fdca70cf33'
    tj = client.TreeherderJob({
        'project': test_project,
        'revision_hash': result_set_stored[0]['revision_hash'],
        'job': {
            'job_guid': job_guid,
            'state': 'completed',
            'log_references': [{
                'url': 'http://ftp.mozilla.org/pub/mozilla.org/spidermonkey/...',
                'name': 'builbot_text',
                'parse_status': 'parsed'
            }]
        }
    })
    tjc.add(tj)

    do_post_collection(test_project, tjc)

    check_artifacts(test_project, job_guid, 'parsed', 0)

    # ensure the parsing didn't happen
    assert mock_parse.called is False


def test_post_job_with_text_log_summary_artifact_parsed(
        test_project,
        monkeypatch,
        result_set_stored,
        mock_post_collection,
        mock_error_summary,
        text_log_summary_blob,
        ):
    """
    test submitting a job with a pre-parsed log gets parse_status of
    "parsed" and doesn't parse the log, but still generates
    the bug suggestions.
    """

    mock_parse = MagicMock(name="parse_line")
    monkeypatch.setattr(StepParser, 'parse_line', mock_parse)

    job_guid = 'd22c74d4aa6d2a1dcba96d95dccbd5fdca70cf33'
    tjc = client.TreeherderJobCollection()
    tj = client.TreeherderJob({
        'project': test_project,
        'revision_hash': result_set_stored[0]['revision_hash'],
        'job': {
            'job_guid': job_guid,
            'state': 'completed',
            'log_references': [{
                'url': 'http://ftp.mozilla.org/pub/mozilla.org/spidermonkey/...',
                'name': 'builbot_text',
                'parse_status': 'parsed'
            }],
            'artifacts': [{
                "blob": json.dumps(text_log_summary_blob),
                "type": "json",
                "name": "text_log_summary",
                "job_guid": job_guid
            }]
        }
    })
    tjc.add(tj)

    do_post_collection(test_project, tjc)

    check_artifacts(test_project, job_guid, 'parsed', 2,
                    {'Bug suggestions', 'text_log_summary'}, mock_error_summary)

    # ensure the parsing didn't happen
    assert mock_parse.called is False


def test_post_job_with_text_log_summary_artifact_pending(
        test_project,
        monkeypatch,
        result_set_stored,
        mock_post_collection,
        mock_error_summary,
        mock_update_parse_status,
        text_log_summary_blob,
        ):
    """
    test submitting a job with a log set to pending, but with a text_log_summary.

    This should detect the artifact, not parse, and just mark the log as parsed,
    then generate bug suggestions.
    """

    mock_parse = MagicMock(name="parse_line")
    monkeypatch.setattr(StepParser, 'parse_line', mock_parse)

    job_guid = 'd22c74d4aa6d2a1dcba96d95dccbd5fdca70cf33'
    tjc = client.TreeherderJobCollection()
    tj = client.TreeherderJob({
        'project': test_project,
        'revision_hash': result_set_stored[0]['revision_hash'],
        'job': {
            'job_guid': job_guid,
            'state': 'completed',
            'log_references': [{
                'url': 'http://ftp.mozilla.org/pub/mozilla.org/spidermonkey/...',
                'name': 'builbot_text',
                'parse_status': 'pending'
            }],
            'artifacts': [{
                "blob": json.dumps(text_log_summary_blob),
                "type": "json",
                "name": "text_log_summary",
                "job_guid": job_guid
            }]
        }
    })

    tjc.add(tj)

    do_post_collection(test_project, tjc)

    check_artifacts(test_project, job_guid, 'parsed', 2,
                    {'Bug suggestions', 'text_log_summary'}, mock_error_summary)

    # ensure the parsing didn't happen
    assert mock_parse.called is False


def test_post_job_with_text_log_summary_and_bug_suggestions_artifact(
        test_project,
        monkeypatch,
        result_set_stored,
        mock_post_collection,
        mock_error_summary,
        text_log_summary_blob,
        ):
    """
    test submitting a job with a pre-parsed log and both artifacts
    does not generate parse the log or generate any artifacts, just uses
    the supplied ones.
    """

    mock_parse = MagicMock(name="parse_line")
    monkeypatch.setattr(StepParser, 'parse_line', mock_parse)
    mock_get_error_summary = MagicMock(name="get_error_summary_artifacts")
    monkeypatch.setattr(error_summary, 'get_error_summary_artifacts', mock_get_error_summary)

    error_summary_blob = ["fee", "fie", "foe", "fum"]

    job_guid = 'd22c74d4aa6d2a1dcba96d95dccbd5fdca70cf33'
    tjc = client.TreeherderJobCollection()
    tj = client.TreeherderJob({
        'project': test_project,
        'revision_hash': result_set_stored[0]['revision_hash'],
        'job': {
            'job_guid': job_guid,
            'state': 'completed',
            'log_references': [{
                'url': 'http://ftp.mozilla.org/pub/mozilla.org/spidermonkey/...',
                'name': 'builbot_text',
                'parse_status': 'parsed'
            }],
            'artifacts': [
                {
                    "blob": json.dumps(text_log_summary_blob),
                    "type": "json",
                    "name": "text_log_summary",
                    "job_guid": job_guid
                },
                {
                    "blob": json.dumps(error_summary_blob),
                    "type": "json",
                    "name": "Bug suggestions",
                    "job_guid": job_guid
                },
            ]
        }
    })

    tjc.add(tj)

    do_post_collection(test_project, tjc)

    check_artifacts(test_project, job_guid, 'parsed', 2,
                    {'Bug suggestions', 'text_log_summary'}, error_summary_blob)

    assert mock_parse.called is False
    assert mock_get_error_summary.called is False


def test_post_job_artifacts_by_add_artifact (
        test_project,
        monkeypatch,
        result_set_stored,
        mock_post_collection,
        mock_error_summary,
        text_log_summary_blob,
        ):
    """
    test submitting a job with a pre-parsed log gets parse_status of
    "parsed" and doesn't parse the log, but still generates
    the bug suggestions.
    """

    mock_parse = MagicMock(name="parse_line")
    monkeypatch.setattr(StepParser, 'parse_line', mock_parse)

    job_guid = 'd22c74d4aa6d2a1dcba96d95dccbd5fdca70cf33'
    tjc = client.TreeherderJobCollection()
    tj = client.TreeherderJob({
        'project': test_project,
        'revision_hash': result_set_stored[0]['revision_hash'],

        "coalesced": [],
        "job": {
            "artifacts": [],
            "build_platform": {
                "architecture": "armv7",
                "os_name": "android",
                "platform": "android-2-3-armv7-api9"
            },
            "build_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/fennec-41.0a1.en-US.android-arm.apk",
            "desc": "",
            "end_timestamp": 1432761770,
            "group_name": "Autophone",
            "group_symbol": "A",
            "job_guid": job_guid,
            "job_symbol": "t",
            "log_references": [
                {
                    "name": "logcat",
                    "parse_status": "parsed",
                    "url": "https://autophone-dev.s3.amazonaws.com/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/autophone-s1s2-s1s2-nytimes-local.ini-1-nexus-one-1-logcat.log"
                },
                {
                    "name": "autophone-nexus-one-1.log",
                    "parse_status": "parsed",
                    "url": "https://autophone-dev.s3.amazonaws.com/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/autophone-autophone-s1s2-s1s2-nytimes-local.ini-1-nexus-one-1.log"
                }
            ],
            "machine": "nexus-one-1",
            "machine_platform": {
                "architecture": "armv7",
                "os_name": "android",
                "platform": "android-2-3-armv7-api9"
            },
            "name": "Autophone Throbber",
            "option_collection": {
                "opt": True
            },
            "product_name": "fennec",
            "reason": "",
            "result": "testfailed",
            "start_timestamp": 1432761256,
            "state": "completed",
            "submit_timestamp": 1432761256,
            "who": ""
        },
    })

    tls_blob = json.dumps({
        "header": {
            "revision": "2cca4c7417b387dd7cfd0cf5672657e0d1748ef0",
            "slave": "nexus-one-1"
        },
        "logurl": "https://autophone-dev.s3.amazonaws.com/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/autophone-autophone-s1s2-s1s2-nytimes-local.ini-1-nexus-one-1.log",
        "step_data": {
             "all_errors": [
                 {"line": "TEST_UNEXPECTED_FAIL | /sdcard/tests/autophone/s1s2test/nytimes.com/index.html | Failed to get uncached measurement.", "linenumber": 64435},
                 {"line": "PROCESS-CRASH | autophone-s1s2 | application crashed [@ libc.so + 0xd01c]", "linenumber": 64435}
             ],
            "errors_truncated": False,
            "steps": [
                {
                    "duration": 514,
                    "error_count": 2,
                    "errors": [
                         {"line": "TEST_UNEXPECTED_FAIL | /sdcard/tests/autophone/s1s2test/nytimes.com/index.html | Failed to get uncached measurement.", "linenumber": 64435},
                         {"line": "PROCESS-CRASH | autophone-s1s2 | application crashed [@ libc.so + 0xd01c]", "linenumber": 64435}
                    ],
                    "finished": "2015-05-27 14:22:50",
                    "finished_linenumber": 1,
                    "name": "step",
                    "order": 0,
                    "result": "testfailed",
                    "started_linenumber": 1
                }
            ]
        }
    })

    ji_blob = json.dumps({
        "job_details": [
            {
                "content_type": "text",
                "title": "Config",
                "value": "s1s2-nytimes-local.ini"
            },
            {
                "content_type": "link",
                "title": "Build",
                "url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/fennec-41.0a1.en-US.android-arm.apk",
                "value": "fennec-41.0a1.en-US.android-arm.apk"
            },
            {
                "content_type": "raw_html",
                "title": "Autophone Throbber-t",
                "value": "12/<em class=\"testfail\">2</em>/0"
            },
            {
                "content_type": "link",
                "title": "phonedash",
                "url": "http://192.168.1.50:18000/#/org.mozilla.fennec/throbberstart/local-blank/norejected/2015-05-26/2015-05-26/notcached/noerrorbars/standarderror/notry",
                "value": "graph"
            },
            {
                "content_type": "link",
                "title": "artifact uploaded",
                "url": "https://autophone-dev.s3.amazonaws.com/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/autophone-s1s2-s1s2-nytimes-local.ini-1-nexus-one-1-logcat.log",
                "value": "logcat"
            },
            {
                "content_type": "link",
                "title": "artifact uploaded",
                "url": "https://autophone-dev.s3.amazonaws.com/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/autophone-s1s2-s1s2-nytimes-local.ini-1-nexus-one-1-60fbf175-e0d3-a181-5777a1bd-3fd4b681.extra",
                "value": "60fbf175-e0d3-a181-5777a1bd-3fd4b681.extra"
            },
            {
                "content_type": "link",
                "title": "artifact uploaded",
                "url": "https://autophone-dev.s3.amazonaws.com/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/autophone-s1s2-s1s2-nytimes-local.ini-1-nexus-one-1-60fbf175-e0d3-a181-5777a1bd-3fd4b681.dmp",
                "value": "60fbf175-e0d3-a181-5777a1bd-3fd4b681.dmp"
            },
            {
                "content_type": "link",
                "title": "artifact uploaded",
                "url": "https://autophone-dev.s3.amazonaws.com/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/autophone-autophone-s1s2-s1s2-nytimes-local.ini-1-nexus-one-1.log",
                "value": "Autophone Log"
            }
        ]
    })

    bapi_blob = json.dumps({
        "buildername": "android-2-3-armv7-api9 mozilla-inbound opt autophone-s1s2"
    })


    pb_blob = json.dumps({
        "build_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/tinderbox-builds/mozilla-inbound-android-api-9/1432676531/en-US/fennec-41.0a1.en-US.android-arm.apk",
        "chunk": 1,
        "config_file": "/mozilla/projects/autophone/src/bclary-autophone/configs/s1s2-nytimes-local.ini"
    })

    tj.add_artifact("text_log_summary", "json", json.dumps(tls_blob))
    tj.add_artifact("Job Info", "json", ji_blob)
    tj.add_artifact("buildapi", "json", bapi_blob)
    tj.add_artifact("privatebuild", "json", pb_blob)

    tjc.add(tj)

    do_post_collection(test_project, tjc)

    check_artifacts(test_project, job_guid, 'parsed', 5,
                    {'Bug suggestions', 'text_log_summary', 'Job Info', 'privatebuild', 'buildapi'}, mock_error_summary)

    # ensure the parsing didn't happen
    assert mock_parse.called is False

