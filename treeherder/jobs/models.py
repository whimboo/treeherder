# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.
from __future__ import unicode_literals

from django.db import models


class BugJobMap(models.Model):
    job = models.ForeignKey('Job')
    bug_id = models.IntegerField()
    type = models.CharField(max_length=50L)
    submit_timestamp = models.IntegerField()
    who = models.CharField(max_length=50L)
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'bug_job_map'


class Job(models.Model):
    id = models.BigIntegerField(primary_key=True)
    job_guid = models.CharField(max_length=50L)
    signature = models.CharField(max_length=50L, blank=True)
    job_coalesced_to_guid = models.CharField(max_length=50L, blank=True)
    result_set = models.ForeignKey('ResultSet')
    build_platform_id = models.IntegerField()
    machine_platform_id = models.IntegerField()
    machine_id = models.IntegerField(null=True, blank=True)
    device_id = models.IntegerField(null=True, blank=True)
    option_collection_hash = models.CharField(max_length=64L, blank=True)
    job_type_id = models.IntegerField()
    product_id = models.IntegerField(null=True, blank=True)
    failure_classification_id = models.IntegerField(null=True, blank=True)
    who = models.CharField(max_length=50L)
    reason = models.CharField(max_length=125L)
    result = models.CharField(max_length=25L, blank=True)
    state = models.CharField(max_length=25L)
    submit_timestamp = models.IntegerField()
    start_timestamp = models.IntegerField(null=True, blank=True)
    end_timestamp = models.IntegerField(null=True, blank=True)
    last_modified = models.DateTimeField()
    pending_eta = models.IntegerField(null=True, blank=True)
    running_eta = models.IntegerField(null=True, blank=True)
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'job'


class JobArtifact(models.Model):
    id = models.BigIntegerField(primary_key=True)
    job = models.ForeignKey(Job)
    name = models.CharField(max_length=50L)
    type = models.CharField(max_length=50L)
    blob = models.TextField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'job_artifact'


class JobEta(models.Model):
    id = models.BigIntegerField(primary_key=True)
    signature = models.CharField(max_length=50L, blank=True)
    state = models.CharField(max_length=25L)
    avg_sec = models.IntegerField()
    median_sec = models.IntegerField()
    min_sec = models.IntegerField()
    max_sec = models.IntegerField()
    std = models.IntegerField()
    sample_count = models.IntegerField()
    submit_timestamp = models.IntegerField()

    class Meta:
        db_table = 'job_eta'


class JobLogUrl(models.Model):
    id = models.BigIntegerField(primary_key=True)
    job = models.ForeignKey(Job)
    name = models.CharField(max_length=50L)
    url = models.CharField(max_length=255L)
    parse_status = models.CharField(max_length=7L, blank=True)
    parse_timestamp = models.IntegerField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'job_log_url'


class JobNote(models.Model):
    id = models.IntegerField(primary_key=True)
    job = models.ForeignKey(Job)
    failure_classification_id = models.IntegerField(null=True, blank=True)
    who = models.CharField(max_length=50L)
    note = models.TextField(blank=True)
    note_timestamp = models.IntegerField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'job_note'


class PerformanceArtifact(models.Model):
    id = models.BigIntegerField(primary_key=True)
    job = models.ForeignKey(Job)
    failure_classification_id = models.IntegerField(null=True, blank=True)
    series_signature = models.CharField(max_length=50L)
    name = models.CharField(max_length=50L)
    type = models.CharField(max_length=50L)
    blob = models.TextField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'performance_artifact'


class PerformanceSeries(models.Model):
    id = models.BigIntegerField(primary_key=True)
    interval_seconds = models.IntegerField()
    series_signature = models.CharField(max_length=50L)
    type = models.CharField(max_length=50L)
    last_updated = models.IntegerField()
    blob = models.TextField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'performance_series'


class ResultSet(models.Model):
    id = models.BigIntegerField(primary_key=True)
    revision_hash = models.CharField(max_length=50L, unique=True)
    aggregate_id = models.CharField(max_length=50L, blank=True)
    result_set_classification_id = models.IntegerField(null=True, blank=True)
    author = models.CharField(max_length=150L)
    type = models.CharField(max_length=25L, blank=True)
    push_timestamp = models.IntegerField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'result_set'


class ResultSetArtifact(models.Model):
    id = models.BigIntegerField(primary_key=True)
    result_set = models.ForeignKey(ResultSet)
    name = models.CharField(max_length=50L)
    type = models.CharField(max_length=50L)
    blob = models.TextField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'result_set_artifact'


class Revision(models.Model):
    id = models.BigIntegerField(primary_key=True)
    revision = models.CharField(max_length=50L)
    author = models.CharField(max_length=150L)
    comments = models.TextField(blank=True)
    commit_timestamp = models.IntegerField(null=True, blank=True)
    files = models.TextField(blank=True)
    repository_id = models.IntegerField()
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'revision'


class RevisionMap(models.Model):
    id = models.BigIntegerField(primary_key=True)
    revision = models.ForeignKey(Revision)
    result_set = models.ForeignKey(ResultSet)
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'revision_map'


class SeriesSignature(models.Model):
    signature = models.CharField(max_length=50L)
    property = models.CharField(max_length=50L)
    value = models.CharField(max_length=150L)
    active_status = models.CharField(max_length=7L, blank=True)

    class Meta:
        db_table = 'series_signature'
