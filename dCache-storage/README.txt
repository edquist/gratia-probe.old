dCache info providers content to Gratia StorageElement and StorageElemenRecord
map.

Please uncomment and edit InfoProviderUrl attribute as set inside
ProbeConfig file. 

The probe reports two types of record structures: StorageElemenmt and
StorageElementRecord. StorageElement describes dCache topology.
StorageElementRecord reports use information relative to corresponding
topology element. There are 4 topology types reported: top level dCache SE,
pools, storage areas , and storage quotas. The first two represent physical
(hardware) layout of the system. The rest are logical view of how storage is
partitioned between user groups.

If you turned on Gratia dCache storage probes you should be able to see the 
accounting information by accessing your Gratia collector. 
To access the information about Gratia dCache-storage probe, go to 
http://<gratia_host>:<gratia_port>/gratia-reporting/, click on "Custom SQL Query" 
on the left site menu frame, enter the following query into provided text box:

select * from StorageElement where ProbeName like 'dcache-storage:<dcache_admin_host_name>';


Detailed description of fields for each record type.

Common fields:
Timestamp: current UTC time in seconds

For all StorageElement records
Version:  as reported by domains/domain/cells/cell/version/metric[ @name =
'release' and . != 'cells' ]
Implementation: dCache
SE: Name of the SE

Top level StorageElement record:
UniqueID and ParentID are the same and are: <SE name>:SE:<SE name>
Space type: SE

Top level StorageElemenetRecord (usage) record:
MeasurementType: raw
StorageType:disk
total space: as reported summary/pools/space/metric total metric
used space: as reported by summary/pools/space/metric used metric
free space: as report by summary/pools/space/metric free metric


Pool records(for each dCache pool):

UniqueID: SE uniqie id
ParentID: <SE name>:Pool:<pool name>
Status: either Closed or Production.  Production if pool heartbeat exists,
positive and  pool enable metric exists

If Status is Production StorageElementRecord corresponding to this pool record
will be reported. Its content will be set to:
MeasurementType: raw
StorageType: disk
total/free/used space are reported as in /pools/pool/space/metric space
metrics group.

Area records
For each link group StorageElement Area record will be created. The 
Area record content will be set to:

UniqueId:  <SE name>:Area:<link group name>
ParentId: SE uniqie id
SpaceType:Area
Status: Production

For each Area record several Quota records may be reported
Each quota record corresponds to a group of space reservations that have the
same description. Quote record content will be set to:
UniqueID: <SE Name>:Quota:<reservation description>
ParentID: Area unique id
Status: Production
SpaceType: Quota

Each quota record will report usage information using corresponding
StorageElementRecord with the following content:
UniqueId: <SE Name>:Quota:<reservation description>
total/free/used space will be reported as sums of all space reservations that
have particular reservation description(as set in current Quota record)

Configuration
Probe supports only two specific configuration options. These are
InfoProviderUrl and ReportPoolUsage. InfoProviderUrl option must point to an
URL of the dCachei info providers root. 
Example: InfoProviderUrl = http://cmsdcam.fnal.gov:2288/info

ReportPoolUsage ( default is on ) , if enabled , stops prob from reporting
dCache pool records. Disable values for this option are: no, n, false, 0
Example: ReportPoolUsage = 1

