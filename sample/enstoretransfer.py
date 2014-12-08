#!/usr/bin/python

#import sys, os, stat
import time
import datetime  # Used for seconds->datetime conversion
#import random
#import pwd, grp
import os
import signal
from urlparse import urlparse

from gratia.common.Gratia import DebugPrint
#import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia

from meter import GratiaProbe, GratiaMeter

from pgpinput import PgInput

def DebugPrintLevel(level, *args):
    if level <= 0:
        level_str = "CRITICAL"
    elif level >= 4:
        level_str = "DEBUG"
    else:
        level_str = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"][level]
    level_str = "%s - EnstoreStorage: " % level_str
    #DBMM
    #print "***MM calling DbP %s %s %s" % (level, level_str, args)
    DebugPrint(level, level_str, *args)


class _EnstoreTransferInputStub:
    """Stub class, needs to be defined before the regular one, to avoid NameError
    """
    """ Query: accounting=> select * from xfer_by_day where date>'2014-08-25';
    date    | storage_group |   read    |    write     | n_read | n_write
------------+---------------+-----------+--------------+--------+---------
 2014-08-26 | ANM           |         0 | 115070377984 |      0 |    7377
 2014-08-27 | ANM           |  11535362 |            0 |      3 |       0
 2014-08-28 | ANM           |  94470144 |            0 |      3 |       0
 2014-08-29 | ALEX          | 900096000 |            0 |      3 |       0

 accounting=> select * from encp_xfer where date > '2014-08-27';
        date         |       node       |  pid  | username |                                                              src                                                               |
                                           dst                                                       |   size    | rw | overall_rate | network_rate | drive_rate |                      volume
             |      mover      |  drive_id   |  drive_sn  |    elapsed    |     media_changer      | mover_interface |   driver   | storage_group |    encp_ip    |               encp_id
| disk_rate | transfer_rate |          encp_version          |   file_family    | wrapper  |  library
---------------------+------------------+-------+----------+--------------------------------------------------------------------------------------------------------------------------------+-----------
-----------------------------------------------------------------------------------------------------+-----------+----+--------------+--------------+------------+--------------------------------------
-------------+-----------------+-------------+------------+---------------+------------------------+-----------------+------------+---------------+---------------+-------------------------------------
+-----------+---------------+--------------------------------+------------------+----------+------------
 2014-08-27 13:58:15 | dmsen03.fnal.gov |  7770 | root     | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/1MB_002        | /dev/null
                                                                                                     |   1048577 | r  |        14636 |      9150443 |     810559 | TST066
             | LTO4_022.mover  | ULTRIUM-TD4 | 1310249035 | 72.5509800911 | SL8500GS.media_changer | enmvr022        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409165822-7770-0
|   9150443 |       4533208 | v3_11c CVS $Revision$ encp.pyc | volume_read_test | cpio_odc | LTO4GS
 2014-08-27 13:58:23 | dmsen03.fnal.gov |  7770 | root     | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/10MB_002       | /dev/null
                                                                                                     |  10485761 | r  |      1571134 |      7546562 |    7455045 | TST066
             | LTO4_022.mover  | ULTRIUM-TD4 | 1310249035 |  7.6930038929 | SL8500GS.media_changer | enmvr022        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409165895-7770-1
|   7546562 |       4215884 | v3_11c CVS $Revision$ encp.pyc | volume_read_test | cpio_odc | LTO4GS
 2014-08-27 13:58:24 | dmsen03.fnal.gov |  7770 | root     | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/1KB_001        | /dev/null
                                                                                                     |      1024 | r  |          783 |     12341860 |      55531 | TST066
             | LTO4_022.mover  | ULTRIUM-TD4 | 1310249035 | 1.61123895645 | SL8500GS.media_changer | enmvr022        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409165903-7770-2
|  12341860 |           914 | v3_11c CVS $Revision$ encp.pyc | volume_read_test | cpio_odc | LTO4GS
 2014-08-28 16:04:53 | dmsen03.fnal.gov |  8583 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ANM.FF1_NEW.cpio_odc/TST084/package-M1W-2014-08-26T17:20:35.959Z.tar              | /volumes/a
ggread/cache/tmp_stage/package-M1W-2014-08-26T17:20:35.959Z/package-M1W-2014-08-26T17:20:35.959Z.tar |  74547200 | r  |       421630 |     60217146 |   39859591 | TST084
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 487.945667982 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ANM           | 131.225.13.26 | dmsen03.fnal.gov-1409259405-8583-0
|  67758717 |      34457635 | v3_11c CVS $Revision$ encp.pyc | FF1_NEW          | cpio_odc | LTO4GS
 2014-08-28 16:04:55 | dmsen06.fnal.gov | 20374 | enstore  | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/torture_test/new_lib/dmsen06/7/dmsen06_f2f6cda82d6e11e4af4700304831518c.data | /dev/null
                                                                                                     |  10485760 | r  |        21336 |     76052612 |   77875300 | common1:ANM.FF1_NEW.cpio_odc:2013-07-
02T14:33:50Z | disk5.mover     | Unknown     | 0          | 492.506582975 | UNKNOWN                | dmsen03         | DiskDriver | ANM           | 131.225.13.37 | dmsen06.fnal.gov-1409259403-20374-0
|  76052612 |      58762140 | v3_11c CVS $Revision$ encp     | FF1_NEW          | cpio_odc | diskSF_NEW
 2014-08-28 16:07:06 | dmsen06.fnal.gov | 20733 | enstore  | /pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/torture_test/new_lib/dmsen06/4/dmsen06_e8ea85a22d6e11e4a6bc00304831518c.data | /dev/null
                                                                                                     |   9437184 | r  |     41230225 |     79026540 |   88431780 | common1:ANM.FF1_NEW.cpio_odc:2013-07-
02T14:33:50Z | disk7.mover     | Unknown     | 0          | 1.27875304222 | UNKNOWN                | dmsen03         | DiskDriver | ANM           | 131.225.13.37 | dmsen06.fnal.gov-1409260025-20733-0
|  79026540 |      61668401 | v3_11c CVS $Revision$ encp     | FF1_NEW          | cpio_odc | diskSF_NEW
 2014-08-29 19:59:27 | dmsen03.fnal.gov | 11611 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T19:21:25.77Z.tar          | /dev/null
                                                                                                     | 300032000 | r  |      2096428 |    112118327 |  135221272 | TST083
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 144.629033089 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ALEX          | 131.225.13.26 | dmsen03.fnal.gov-1409360223-11611-0
| 112118327 |     107459278 | v3_11c CVS $Revision$ encp.pyc | TestClone_7      | cpio_odc | LTO4GS
 2014-08-29 20:00:34 | dmsen03.fnal.gov | 11611 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T19:27:56.844Z.tar         | /dev/null
                                                                                                     | 300032000 | r  |      4526877 |     80136089 |   85963956 | TST083
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 67.3343689442 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ALEX          | 131.225.13.26 | dmsen03.fnal.gov-1409360367-11611-1
|  80136089 |      77746704 | v3_11c CVS $Revision$ encp.pyc | TestClone_7      | cpio_odc | LTO4GS
 2014-08-29 20:02:16 | dmsen03.fnal.gov | 11611 | root     | /pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T18:58:22.864Z.tar         | /dev/null
                                                                                                     | 300032000 | r  |      2987800 |    111891277 |  135991153 | TST083
             | LTO4_021B.mover | ULTRIUM-TD4 | 1310206564 | 101.175196171 | SL8500GS.media_changer | enmvr021        | FTTDriver  | ALEX          | 131.225.13.26 | dmsen03.fnal.gov-1409360435-11611-2
| 111891277 |     107261667 | v3_11c CVS $Revision$ encp.pyc | TestClone_7      | cpio_odc | LTO4GS
"""

    value_matrix_summ = [['2014-08-26', 'ANM', 0, 115070377984, 0, 7377],
                     ['2014-08-27', 'ANM', 11535362, 115070377984, 3, 7377],
                     ['2014-08-28', 'ANM', 94470144, 0, 3, 0],
                     ['2014-08-29', 'ALEX', 900096000, 0, 3, 0]
                    ]
    # date,node,username,src,dst,size,rw,overall_rate,mover_interface,storage_group,encp_id
    value_matrix = [['2014-08-27 13:58:15', 'dmsen03.fnal.gov', 'root', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/1MB_002', '/dev/null', 1048577, 'r', 14636, 'enmvr022', 'ANM', 'dmsen03.fnal.gov-1409165822-7770-0'],
                     ['2014-08-27 13:58:23', 'dmsen03.fnal.gov', 'root', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/10MB_002', '/dev/null', 10485761, 'r', 1571134, 'enmvr022', 'ANM', 'dmsen03.fnal.gov-1409165895-7770-1'],
                     ['2014-08-27 13:58:24', 'dmsen03.fnal.gov', 'root', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/tape/encp_test_for_enstore/file_clerk3/test_files_for_enstore/1KB_001', '/dev/null', 1024, 'r', 783, 'enmvr022', 'ANM', 'dmsen03.fnal.gov-1409165903-7770-2'],
                     ['2014-08-28 16:04:53', 'dmsen03.fnal.gov', 'root', '/pnfs/fs/usr/data2/file_aggregation/packages/ANM.FF1_NEW.cpio_odc/TST084/package-M1W-2014-08-26T17:20:35.959Z.tar', '/volumes/aggread/cache/tmp_stage/package-M1W-2014-08-26T17:20:35.959Z/package-M1W-2014-08-26T17:20:35.959Z.tar', 74547200, 'r', 421630, 'enmvr021', 'ANM', 'dmsen03.fnal.gov-1409259405-8583-0'],
                     ['2014-08-28 16:04:55', 'dmsen06.fnal.gov', 'enstore', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/torture_test/new_lib/dmsen06/7/dmsen06_f2f6cda82d6e11e4af4700304831518c.data', '/dev/null', 10485760, 'r', 21336, 'dmsen03', 'ANM', 'dmsen06.fnal.gov-1409259403-20374-0'],
                     ['2014-08-28 16:07:06', 'dmsen06.fnal.gov', 'enstore', '/pnfs/fs/usr/data2/file_aggregation/LTO4/moibenko/torture_test/new_lib/dmsen06/4/dmsen06_e8ea85a22d6e11e4a6bc00304831518c.data', '/dev/null', 9437184, 'r', 41230225, 'dmsen03', 'ANM', 'dmsen06.fnal.gov-1409260025-20733-0'],
                     ['2014-08-29 19:59:27', 'dmsen03.fnal.gov', 'root', '/pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T19:21:25.77Z.tar', '/dev/null', 300032000, 'r', 2096428, 'enmvr021', 'ALEX', 'dmsen03.fnal.gov-1409360223-11611-0'],
                     ['2014-08-29 20:00:34', 'dmsen03.fnal.gov', 'root', '/pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T19:27:56.844Z.tar', '/dev/null', 300032000, 'r', 4526877, 'enmvr021', 'ALEX', 'dmsen03.fnal.gov-1409360367-11611-1'],
                     ['2014-08-29 20:02:16', 'dmsen03.fnal.gov', 'root', '/pnfs/fs/usr/data2/file_aggregation/packages/ALEX.TestClone_7.cpio_odc/TST083/package-M2W-2014-07-30T18:58:22.864Z.tar', '/dev/null', 300032000, 'r', 2987800, 'enmvr021', 'ALEX', 'dmsen03.fnal.gov-1409360435-11611-2']
    ]

    def get_records_summary():
        for i in _EnstoreTransferInputStub.value_matrix_summ:
            retv = {'date': i[0],
                    'storage_group': i[1],
                    'read': i[2],
                    'write': i[3],
                    'n_read': i[4],
                    'n_write': i[5]
                    }
            yield retv
    get_records_summary = staticmethod(get_records_summary)

    def get_records():
        for i in _EnstoreTransferInputStub.value_matrix:
            retv = {'date': i[0],
                    'node':i[1],
                    'username': i[2],
                    'src': i[3],
                    'dst': i[4],
                    'size': i[5],
                    'rw': i[6],
                    'overall_rate': i[7],
                    'mover_interface': i[8],
                    'storage_group': i[9],
                    'encp_id': i[10]
                    }
            yield retv
    get_records = staticmethod(get_records)


class EnstoreTransferInput(PgInput):
    """Get transfer information from the Enstore accounting DB
    """

    VERSION_ATTRIBUTE = 'EnstoreVersion'

    def get_init_params(self):
        """Return list of parameters to read form the config file"""
        return PgInput.get_init_params(self) + [EnstoreTransferInput.VERSION_ATTRIBUTE]

    def start(self, static_info):
        """open DB connection and set version form config file"""
        PgInput.start(self, static_info)
        DebugPrint(4, "ETI start, static info: %s" % static_info)
        if EnstoreTransferInput.VERSION_ATTRIBUTE in static_info:
            self._set_version_config(static_info[EnstoreTransferInput.VERSION_ATTRIBUTE])

    def _start_stub(self, static_info):
        """start replacement for testing: database connection errors are trapped"""
        try:
            DebugPrintLevel(4, "Testing DB connection. The probe will not use it")
            PgInput.start(self, static_info)
            if self.status_ok():
                DebugPrintLevel(4, "Connection successful")
            else:
                DebugPrintLevel(4, "Connection failed")
            DebugPrintLevel(4, "Closing the connection")
            self.stop()
        except:
            DebugPrint(1, "Database connection failed. The test can continue since stubs are used.")
        DebugPrint(4, "ETI start stub, static info: %s" % static_info)
        if EnstoreTransferInput.VERSION_ATTRIBUTE in static_info:
            self._set_version_config(static_info[EnstoreTransferInput.VERSION_ATTRIBUTE])

    def get_version(self):
        # RPM package is 'enstore'
        return self._get_version('enstore')

    def get_records(self, limit=None):
        """Select the transfer records from the transfer table
        accounting=> \d encp_xfer;
                Table "public.encp_xfer"
    Column      |            Type             | Modifiers
-----------------+-----------------------------+-----------
date            | timestamp without time zone | not null - StartTime
node            | character varying           | not null - hostname?
pid             | integer                     | not null
username        | character varying(32)       | not null - LocalUser
src             | text                        | not null +- FileName (depending on direction)
dst             | text                        | not null +
size            | bigint                      | not null - size in Network
rw              | character(1)                | not null - isNew r->0, w->1
overall_rate    | bigint                      | not null
network_rate    | bigint                      | not null
drive_rate      | bigint                      | not null
volume          | character varying           | not null
mover           | character varying(32)       | not null
drive_id        | character varying(16)       | not null
drive_sn        | character varying(16)       | not null
elapsed         | double precision            | not null
media_changer   | character varying(32)       | not null
mover_interface | character varying(32)       | not null
driver          | character varying(16)       | not null
storage_group   | character varying(16)       | not null
encp_ip         | character varying(16)       | not null
encp_id         | character varying(64)       | not null
disk_rate       | bigint                      |
transfer_rate   | bigint                      |
encp_version    | character varying(48)       |
file_family     | character varying           |
wrapper         | character varying           |
library         | character varying           |
Indexes:
    "encp_error_library_idx" btree (library)
    "encp_xfer_library_idx" btree (library)
    "xfr_date_idx" btree (date)
    "xfr_file_family_idx" btree (file_family)
    "xfr_media_changer_idx" btree (media_changer)
    "xfr_mover_idx" btree (mover)
    "xfr_node_idx" btree (node)
    "xfr_oid_idx" btree (oid)
    "xfr_pid_idx" btree (pid)
    "xfr_storage_group_idx" btree (storage_group)
    "xfr_user_idx" btree (username)
    "xfr_volume_idx" btree (volume)
    "xfr_wrapper_idx" btree (wrapper)
        """
        checkpoint = self.checkpoint
        if checkpoint:
            checkpoint_sql = "WHERE date >= '%s'" % GratiaProbe.format_date(checkpoint.date())
        else:
            checkpoint_sql = ""
        if limit:
            limit_sql = "LIMIT %s" % limit
        else:
            limit_sql = ""

        sql = '''SELECT
            date,
            node,
            username,
            src, dst,
            size,
            rw,
            overall_rate,
            mover_interface,
            storage_group,
            encp_id
            FROM encp_xfer
            %s
            ORDER BY date, storage_group
            %s''' % (checkpoint_sql, limit_sql)

        DebugPrint(4, "Requesting new Enstore records %s" % sql)
        new_checkpoint = None
        for r in self.query(sql):
            yield r
            if checkpoint:
                # psycopg2 returns datetime obj (ok for checkpoint)
                #  timestamp->datetime, timestamp without time zone -> float (seconds since Epoch)
                new_date = GratiaProbe.parse_date(r['date'])
                if new_checkpoint is None or new_date > new_checkpoint:
                    new_checkpoint = new_date
        if new_checkpoint:
            print "****** MMDB Saving New Checkpoint: %s, %s, %s" % (type(new_checkpoint), new_checkpoint, datetime.datetime.fromtimestamp(new_checkpoint))
            checkpoint.set_date_transaction(datetime.datetime.fromtimestamp(new_checkpoint))

    def get_records_summary(self, limit=None):
        """Select the transfer records from the daily summary table
        accounting=> \d xfer_by_day;
         Table "public.xfer_by_day"
    Column     |       Type        | Modifiers
---------------+-------------------+-----------
 date          | date              | not null
 storage_group | character varying | not null
 read          | bigint            |
 write         | bigint            |
 n_read        | bigint            |
 n_write       | bigint            |
Indexes:
    "xfer_by_date_pkey" PRIMARY KEY, btree (date, storage_group)
Daily summary pre-calculated by trigger in the enstore DB

We are interested in

        """
        # TODO: is daily summary OK or detailed values are needed?

        checkpoint = self.checkpoint
        if checkpoint:
            checkpoint_sql = "WHERE date >= '%s'" % GratiaProbe.format_date(checkpoint.date())
        else:
            checkpoint_sql = ""
        if limit:
            limit_sql = "LIMIT %s" % limit
        else:
            limit_sql = ""

        sql = '''SELECT
            date,
            storage_group,
            read, write,
            n_read, n_write
            FROM xfer_by_day
            %s
            ORDER BY date, storage_group
            %s ''' % (checkpoint_sql, limit_sql)

        DebugPrint(4, "Requesting new Enstore records %s" % sql)

        new_checkpoint = None
        for r in self.query(sql):
            yield r
            if checkpoint:
                # psycopg2 returns datetime obj (ok for checkpoint)
                #  timestamp->datetime, timestamp without time zone -> float (seconds since Epoch)
                new_date = GratiaProbe.parse_date(r['date'])
                if new_checkpoint is None or new_date > new_checkpoint:
                    new_checkpoint = new_date
        if new_checkpoint:
            checkpoint.set_date_transaction(new_checkpoint)

    def _get_records_stub(self):
        """get_records replacement for tests: records are from a pre-filled array"""
        for i in _EnstoreTransferInputStub.get_records():
            yield i

    def do_test(self):
        """Test with pre-arranged DB query results
        replacing: start, get_records
        """
        # replace DB calls with stubs
        self.start = self._start_stub
        self.get_records = self._get_records_stub


class EnstoreTransferProbe(GratiaMeter):

    PROBE_NAME = 'enstoretransfer'
    # dCache, xrootd, Enstore
    SE_NAME = 'Enstore'
    # Production
    SE_STATUS = 'Production'
    # disk, tape
    SE_TYPE = 'tape'
    # raw, logical
    SE_MEASUREMENT_TYPE = 'logical'

    def __init__(self):
        GratiaMeter.__init__(self, self.PROBE_NAME)
        self._probeinput = EnstoreTransferInput()

    #def get_storage_element(self, unique_id, site, name, parent_id=None, timestamp=None):
    #    return gse

    #def get_storage_element_record(self, unique_id, timestamp=None):
    #    return gser

    #def input_to_gsrs(self, inrecord, selement, serecord):
    #    """Add input values to storage element and storage element record
    #    Return the tuple VO,tot,free,used,f_tot,f_used to allow cumulative counters
    #    """
    #    return inrecord['storage_group'], total, total-used, used, 0, inrecord['active_files']

    def get_usage_record(self):
        r = Gratia.UsageRecord("Storage")
        r.AdditionalInfo("Protocol", "enstore")
        r.Grid("Local")
        # Needs to be here, cannot be NULL
        r.Status(0)
        return r

    def URL2host(self, urltoparse):
        tmp = urlparse(urltoparse)
        if tmp.hostname:
            return tmp.hostname
        return self.get_hostname()

    def main(self):
        # Initialize the probe an the input
        self.start()
        DebugPrintLevel(4, "Enstore transfer probe started")

        se = self.get_sitename()
        name = self.get_probename()
        #timestamp = time.time()

        # Parent storage element
        #DebugPrintLevel(4, "Sending the parent StorageElement (%s/%s)" % (se, name))
        #unique_id = "%s:SE:%s" % (se, se)
        #parent_id = unique_id
        #gse = self.get_storage_element(unique_id, se, name, timestamp=timestamp)
        #Gratia.Send(gse)
        # TODO: is a SER with totals needed?

        hostname = self.get_hostname()

        # Loop over storage records
        for srecord in self._probeinput.get_records():
            """
            date,
            node, pid,
            username,
            src, dst,
            size,
            rw,
            mover_interface,
            storage_group
            encp_id
            """
            DebugPrint(5, "Preparing transfer record for: %s" % srecord)
            if srecord['rw'] == 'w':
                # write
                isNew = self._isWrite2isNew(True)
                src = self._normalize_hostname(srecord['node'])
                dst = self._normalize_hostname(srecord['mover_interface'])
                filepath = srecord['dst']
            else:
                # read
                isNew = self._isWrite2isNew(False)
                src = self._normalize_hostname(srecord['mover_interface'])
                dst = self._normalize_hostname(srecord['node'])
                filepath = srecord['src']
            r = self.get_usage_record()
            vo_name = srecord['storage_group']
            r.VOName(vo_name)
            r.AdditionalInfo("Source", src)
            r.AdditionalInfo("Destination", dst)
            r.AdditionalInfo("Protocol", "enstore")
            r.AdditionalInfo("IsNew", isNew)
            r.AdditionalInfo("File", filepath)
            # uniq_id = "%s.%s" % (srecord['node'], srecord['pid'])
            uniq_id = srecord['encp_id']
            r.LocalJobId(uniq_id)
            r.Grid("Local")
            # psycopg2 returns datetime obj, StartTime requires float or string
            r.StartTime(self.format_date(srecord['date']))
            # srecord['size'] is always in bytes
            # Network(self, value, storageUnit=r'', phaseUnit=r'', metric='total', description=r'')
            # Metric should be one of 'total','average','max','min'
            # phaseUnit (duration) if numeric s considered to be in seconds and is converted in ISO timestamp
            size = srecord['size']
            rate = srecord['overall_rate']
            if rate == 0:
                if size == 0:
                    duration = 0
                    r.WallDuration(duration)
                else:
                    duration = ''
            else:
                duration = size/srecord['overall_rate']
                r.WallDuration(duration)
            r.Network(size, 'b', duration, "transfer")
            r.LocalUserId(srecord['username'])
            r.SubmitHost(srecord['node'])
            #r.Status(0)
            # Future modifications of Enstore may include a DN
            r.DN("/OU=UnixUser/CN=%s" % srecord['username'])
            DebugPrint(4, "Sending transfer record for VO %s: %s" % (vo_name, uniq_id))
            Gratia.Send(r)


            """ Summary record
            #vo_name = srecord['storage_group']
            # Avoid empty records
            if srecord['read']+srecord['write']+srecord['n_read']+srecord['n_write'] == 0:
                continue
            if srecord['read']>0:
                # outgoing traffic
                r = self.get_usage_record()
                r.AdditionalInfo("Source", hostname)
                # unknown destination: r.AdditionalInfo("Destination", dstHost)
                r.AdditionalInfo("Protocol", "enstore")
                r.AdditionalInfo("IsNew", isNew)
            """
            #    # The query sorted the results by time_end, so our last value will
            #    # be the greatest
            #    time_end = job['time_end']
            #    self.checkpoint.val = time_end

            # If we found at least one record, but the time_end has not increased since
            # the previous run, increase the checkpoint by one so we avoid continually
            # reprocessing the last records.
            # (This assumes the probe won't be run more than once per second.)
            #if self.checkpoint.val == time_end:
            #    self.checkpoint.val = time_end + 1



if __name__ == "__main__":
    # Do the work
    EnstoreTransferProbe().main()



