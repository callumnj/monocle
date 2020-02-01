# MIT License
# Copyright (c) 2019 Fabien Boucher

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import statistics
from elasticsearch.helpers import scan as scanner
from itertools import groupby
from datetime import datetime


def generate_filter(repository_fullname, params):
    gte = params.get('gte')
    lte = params.get('lte')
    on_cc_gte = params.get('on_cc_gte')
    on_cc_lte = params.get('on_cc_lte')
    etype = params.get('etype')
    author = params.get('author')
    approval = params.get('approval')
    state = params.get('state')
    ec_same_date = params.get('ec_same_date')

    if isinstance(etype, str):
        etype = list(etype)

    created_at_range = {
        "created_at": {
            "format": "epoch_millis"
        }
    }
    on_created_at_range = {
        "on_created_at": {
            "format": "epoch_millis"
        }
    }
    if gte:
        created_at_range['created_at']['gte'] = gte
    if lte:
        created_at_range['created_at']['lte'] = lte
    if ec_same_date:
        on_cc_gte = gte
        on_cc_lte = lte
    if on_cc_gte or ec_same_date:
        on_created_at_range['on_created_at']['gte'] = on_cc_gte
    if on_cc_lte or ec_same_date:
        on_created_at_range['on_created_at']['lte'] = on_cc_lte
    qfilter = [
        {"regexp": {
            "repository_fullname": {
                "value": repository_fullname}}},
        {"range": created_at_range},
        {"range": on_created_at_range},
    ]
    if etype:
        qfilter.append({"terms": {"type": etype}})
    if author:
        qfilter.append({"term": {"author": author}})
    if state:
        qfilter.append({"term": {"state": state}})
    if approval:
        qfilter.append({'term': {"approval": approval}})
    return qfilter


def generate_must_not(params, exclude_change=True):
    must_not = []
    if params['exclude_authors']:
        must_not.append(
            {
                "terms": {
                    "author": params['exclude_authors']
                }
            }
        )
    if exclude_change:
        must_not.append(
            {
                "term": {
                    "type": "Change"
                }
            }
        )
    return must_not


def set_params_defaults(params):
    " Apply default values to params"
    return {
        'gte': params.get('gte'),
        'lte': params.get('lte'),
        'on_cc_gte': params.get('on_cc_gte'),
        'on_cc_lte': params.get('on_cc_lte'),
        'ec_same_date': params.get('ec_same_date'),
        'etype': params.get('etype'),
        'author': params.get('author'),
        'interval': params.get('interval', '3h'),
        'size': params.get('size', 10),
        'exclude_authors': params.get('exclude_authors', []),
        'approval': params.get('approval'),
    }


def run_query(es, index, body):
    search_params = {
        'index': index, 'doc_type': index, 'body': body}
    try:
        res = es.search(**search_params)
    except Exception:
        return []
    return res


def _scan_events(es, index, repository_fullname, params):
    body = {
        # "_source": "repository_fullname_and_number",
        "_source": params.get('field', []),
        "query": {
            "bool": {
                "filter": generate_filter(repository_fullname, params),
                "must_not": generate_must_not(params)
            }
        }
    }
    scanner_params = {
        'index': index, 'doc_type': index, 'query': body}
    data = scanner(es, **scanner_params)
    return [d['_source'] for d in data]


def count_events(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    body = {
        "query": {
            "bool": {
                "filter": generate_filter(repository_fullname, params),
                "must_not": generate_must_not(params)
            }
        }
    }
    params = {'index': index, 'doc_type': index}
    params['body'] = body
    try:
        res = es.count(**params)
    except Exception:
        return {}
    return res['count']


def count_authors(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    body = {
        "aggs": {
            "agg1": {
                "cardinality": {
                    "field": "author",
                    "precision_threshold": 3000,
                }
            }
        },
        "size": 0,
        "query": {
            "bool": {
                "filter": generate_filter(repository_fullname, params),
                "must_not": generate_must_not(params)
            }
        }
    }
    data = run_query(es, index, body)
    return data['aggregations']['agg1']['value']


def events_histo(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    body = {
        "aggs": {
            "agg1": {
                "date_histogram": {
                    "field": "created_at",
                    "interval": params['interval'],
                }
            },
            "avg_count": {
                "avg_bucket": {
                    "buckets_path": "agg1>_count"
                }
            }
        },
        "size": 0,
        "query": {
            "bool": {
                "filter": generate_filter(repository_fullname, params),
                "must_not": generate_must_not(params)
            }
        }
    }
    data = run_query(es, index, body)
    return (
        data['aggregations']['agg1']['buckets'],
        data['aggregations']['avg_count']['value'])


def _events_top(
        es, index, repository_fullname, field, params):
    body = {
        "aggs": {
            "agg1": {
                "terms": {
                    "field": field,
                    "size": params['size'],
                    "order": {
                        "_count": "desc"
                    }
                }
            }
        },
        "size": 0,
        "query": {
            "bool": {
                "filter": generate_filter(repository_fullname, params),
                "must_not": generate_must_not(params)
            }
        }
    }
    data = run_query(es, index, body)
    count_series = [
        b['doc_count'] for b in
        data['aggregations']['agg1']['buckets']]
    count_avg = (statistics.mean(count_series)
                 if count_series else 0)
    count_median = (statistics.median(sorted(count_series))
                    if count_series else 0)
    return {
        'buckets': data['aggregations']['agg1']['buckets'],
        'count_avg': count_avg, 'count_median': count_median}


def events_top_authors(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    return _events_top(
        es, index, repository_fullname, "author", params)


def changes_top_approval(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = "ChangeReviewedEvent"
    return _events_top(
        es, index, repository_fullname, "approval", params)


def changes_top_commented(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = "ChangeCommentedEvent"
    return _events_top(
        es, index, repository_fullname, "repository_fullname_and_number",
        params)


def changes_top_reviewed(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = "ChangeReviewedEvent"
    return _events_top(
        es, index, repository_fullname, "repository_fullname_and_number",
        params)


def authors_top_reviewed(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = "ChangeReviewedEvent"
    return _events_top(
        es, index, repository_fullname, "on_author", params)


def authors_top_commented(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = "ChangeCommentedEvent"
    return _events_top(
        es, index, repository_fullname, "on_author", params)


def peers_exchange_strength(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = ("ChangeReviewedEvent", "ChangeCommentedEvent")
    authors = [bucket['key'] for bucket in _events_top(
        es, index, repository_fullname, "author", params)['buckets']]
    peers_strength = {}
    for author in authors:
        params['author'] = author
        for bucket in _events_top(
                es, index, repository_fullname, "on_author",
                params)['buckets']:
            if bucket['key'] == author:
                continue
            peers_id = tuple(sorted((author, bucket['key'])))
            peers_strength.setdefault(peers_id, 0)
            peers_strength[peers_id] += bucket['doc_count']
    peers_strength = sorted(
        [(peers_id, strength) for peers_id, strength in
         peers_strength.items()],
        key=lambda x: x[1], reverse=True)
    return(peers_strength)


def change_merged_count_by_duration(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = ("Change",)
    params['state'] = "MERGED"
    body = {
        "aggs": {
            "agg1": {
                "range": {
                    "field": "duration",
                    "ranges": [
                        {
                            "to": 24*3600
                        },
                        {
                            "from": 24*3600+1,
                            "to": 7*24*3600
                        },
                        {
                            "from": 7*24*3600+1,
                            "to": 31*24*3600
                        },
                        {
                            "from": 31*24*3600+1
                        },
                    ],
                    "keyed": True
                }
            }
        },
        "size": 0,
        "query": {
            "bool": {
                "filter": generate_filter(repository_fullname, params),
                "must_not": generate_must_not(params, exclude_change=False)
            }
        }
    }
    data = run_query(es, index, body)
    return data['aggregations']['agg1']['buckets']


def pr_merged_avg_duration(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = ("Change",)
    params['state'] = "MERGED"
    body = {
        "aggs": {
            "agg1": {
                "avg": {
                    "field": "duration"
                }
            }
        },
        "size": 0,
        "docvalue_fields": [
            {
                "field": "created_at",
                "format": "date_time"
            },
        ],
        "query": {
            "bool": {
                "filter": generate_filter(repository_fullname, params),
                "must_not": generate_must_not(params, exclude_change=False)
            }
        }
    }
    data = run_query(es, index, body)
    return data['aggregations']['agg1']


def changes_events_counters(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    ret = {}
    for etype in (
            "ChangeCreatedEvent", "ChangeReviewedEvent",
            "ChangeCommentedEvent", "ChangeAbandonedEvent",
            "ChangeMergedEvent"):
        params['etype'] = (etype,)
        events_count = count_events(es, index, repository_fullname, params)
        authors_count = count_authors(es, index, repository_fullname, params)
        ret[etype] = {
            'events_count': events_count,
            'authors_count': authors_count}
    return ret


def changes_closed_ratios(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    etypes = (
        'ChangeCreatedEvent', "ChangeMergedEvent", "ChangeAbandonedEvent")
    ret = {}
    for etype in etypes:
        params['etype'] = (etype,)
        ret[etype] = count_events(es, index, repository_fullname, params)
    ret['merged/created_ratio'] = round(
        ret['ChangeMergedEvent'] / ret['ChangeCreatedEvent'] * 100, 1)
    ret['abandoned/created_ratio'] = round(
        ret['ChangeAbandonedEvent'] / ret['ChangeMergedEvent'] * 100, 1)
    for etype in etypes:
        del ret[etype]
    return ret


def _first_event_on_changes(es, index, repository_fullname, params):
    def keyfunc(x):
        return x['repository_fullname_and_number']
    groups = {}
    params = set_params_defaults(params)
    _events = _scan_events(es, index, repository_fullname, params)
    _events = sorted(
        _events, key=lambda k: k['repository_fullname_and_number'])
    # Keep by PR the created date + first event date
    for pr, events in groupby(_events, keyfunc):
        groups[pr] = {
            'change_created_at': None,
            'first_event_created_at': datetime.now(),
            'first_event_author': None,
            'delta': None}
        for event in events:
            if not groups[pr]['change_created_at']:
                groups[pr]['change_created_at'] = datetime.strptime(
                    event['on_created_at'], "%Y-%m-%dT%H:%M:%SZ")
            event_created_at = datetime.strptime(
                event['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            if event_created_at < groups[pr]['first_event_created_at']:
                groups[pr]['first_event_created_at'] = event_created_at
                groups[pr]['delta'] = (
                    groups[pr]['first_event_created_at'] -
                    groups[pr]['change_created_at'])
                groups[pr]['first_event_author'] = event['author']
    ret = {
        'first_event_delay_avg': 0,
        'top_authors': {}}
    for pr_data in groups.values():
        ret['first_event_delay_avg'] += pr_data['delta'].seconds
        ret['top_authors'].setdefault(pr_data['first_event_author'], 0)
        ret['top_authors'][pr_data['first_event_author']] += 1
    ret['first_event_delay_avg'] = int(
        ret['first_event_delay_avg'] / len(groups))
    ret['top_authors'] = sorted(
        [(k, v) for k, v in ret['top_authors'].items()],
        key=lambda x: x[1], reverse=True)[:10]
    return ret


def first_comment_on_changes(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = ('ChangeCommentedEvent',)
    return _first_event_on_changes(es, index, repository_fullname, params)


def first_review_on_changes(es, index, repository_fullname, params):
    params = set_params_defaults(params)
    params['etype'] = ('ChangeReviewedEvent',)
    return _first_event_on_changes(es, index, repository_fullname, params)
