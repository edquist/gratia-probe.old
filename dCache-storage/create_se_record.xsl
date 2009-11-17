<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://www.dcache.org/2008/01/Info">

<xsl:output method="xml" encoding="iso-8859-1" omit-xml-declaration="yes" indent="yes" />

<xsl:param name="SE"/>
<xsl:param name="now" />

<xsl:key name="resDescr" match="dc:reservation" use="dc:metric[ @name = 'description']"/>

<xsl:template match="/dc:dCache">

<xsl:variable name="version" select="dc:domains/dc:domain/dc:cells/dc:cell/dc:version/dc:metric[ @name = 'release' and . != 'cells' ]"/>

<xsl:variable name="uniqId" select="concat($SE,':SE:',$SE)"/>
<xsl:variable name="parentId" select="concat($SE,':SE:',$SE)"/>

<xsl:variable name="sspace" select="dc:summary/dc:pools/dc:space/dc:metric"/>

<Result>

 <setArray><array>
 <StorageElement.StorageElement>
       <UniqueID><xsl:value-of select="$uniqId"/></UniqueID>
       <ParentID><xsl:value-of select="$parentId"/></ParentID>
       <Name><xsl:value-of select="$SE"/></Name>
       <SE><xsl:value-of select="$SE"/></SE>
       <SpaceType>SE</SpaceType>
       <Implementation>dCache</Implementation>
       <Version><xsl:value-of select="$version"/></Version>
       <Timestamp type="numeric" ><xsl:value-of select="$now"/></Timestamp>
       <Status>Production</Status>
    </StorageElement.StorageElement>

    <StorageElementRecord.StorageElementRecord>
       <UniqueID><xsl:value-of select="$uniqId"/></UniqueID>
       <MeasurementType>raw</MeasurementType>
       <StorageType>disk</StorageType>
       <TotalSpace><xsl:value-of select="$sspace[ @name = 'total' ]"/></TotalSpace>
       <FreeSpace><xsl:value-of select="$sspace[ @name = 'free' ]"/></FreeSpace>
       <UsedSpace><xsl:value-of select="$sspace[ @name = 'used' ]"/></UsedSpace>
    </StorageElementRecord.StorageElementRecord>

<xsl:for-each select="dc:pools/dc:pool">

    <xsl:variable name="uniqId" select="concat($SE,':SE:',@name)"/>

    <xsl:variable name="status">
        <xsl:choose>
            <xsl:when test="dc:metric[ @name = 'enabled' and . = 'true'] and dc:metric[ @name = 'last-heartbeat' and . > 0 ]">Production</xsl:when>
              <xsl:otherwise>Closed</xsl:otherwise>
        </xsl:choose>
    </xsl:variable>

    <xsl:variable name="space" select="dc:space/dc:metric"/>

    <StorageElement.StorageElement>
       <UniqueID><xsl:value-of select="$uniqId"/></UniqueID>
       <ParentID><xsl:value-of select="$parentId"/></ParentID>
       <Name><xsl:value-of select="@name"/></Name>
       <SE><xsl:value-of select="$SE"/></SE>
       <SpaceType>Pool</SpaceType>
       <Implementation>dCache</Implementation>
       <Version><xsl:value-of select="$version"/></Version>
       <Timestamp type="numeric" ><xsl:value-of select="$now"/></Timestamp>
       <Status><xsl:value-of select="$status"/></Status>
    </StorageElement.StorageElement>
    <StorageElementRecord.StorageElementRecord>
       <UniqueID><xsl:value-of select="$uniqId"/></UniqueID>
       <MeasurementType>raw</MeasurementType>
       <StorageType>disk</StorageType>
       <TotalSpace><xsl:value-of select="$space[ @name = 'total' ]"/></TotalSpace>
       <FreeSpace><xsl:value-of select="$space[ @name = 'free' ]"/></FreeSpace>
       <UsedSpace><xsl:value-of select="$space[ @name = 'used' ]"/></UsedSpace>
    </StorageElementRecord.StorageElementRecord>

</xsl:for-each>
<xsl:for-each select="dc:linkgroups/dc:linkgroup">

  <xsl:variable name="name" select="dc:metric[ @name = 'name']"/>
  <xsl:variable name="linkUniqId" select="concat($SE,':Area:',$name)"/>


    <StorageElement.StorageElement>
       <UniqueID><xsl:value-of select="$linkUniqId"/></UniqueID>
       <ParentID><xsl:value-of select="$parentId"/></ParentID>
       <Name><xsl:value-of select="$name"/></Name>
       <SE><xsl:value-of select="$SE"/></SE>
       <SpaceType>Area</SpaceType>
       <Implementation>dCache</Implementation>
       <Version><xsl:value-of select="$version"/></Version>
       <Timestamp type="numeric"><xsl:value-of select="$now"/></Timestamp>
       <Status>Production</Status>
    </StorageElement.StorageElement>

  <xsl:variable name="linkId" select="@lgid"/>

  <xsl:variable name="reservations" select="../../dc:reservations/dc:reservation/dc:metric[ @name ='linkgroupref' and . = $linkId]/.."/>

  <xsl:for-each select="$reservations">
     <xsl:if test="generate-id(.) = generate-id(key('resDescr',dc:metric[ @name = 'description'])[1])">
         <xsl:variable name="spaceName" select="dc:metric[ @name='description']"/>

         <xsl:variable name="space" select="$reservations/dc:metric[ @name = 'description' and . = $spaceName]/../dc:space/dc:metric"/>

         <xsl:variable name="totalSpace" select="sum($space[ @name = 'total' ])"/>
         <xsl:variable name="freeSpace" select="sum($space[ @name = 'free' ])"/>
         <xsl:variable name="usedSpace" select="sum($space[ @name = 'used' ])"/>

         <xsl:variable name="uniqId" select="concat($SE,':Quota:',$spaceName)"/>

         <StorageElement.StorageElement>
           <UniqueID><xsl:value-of select="$uniqId"/></UniqueID>
           <ParentID><xsl:value-of select="$linkUniqId"/></ParentID>
           <Name><xsl:value-of select="$spaceName"/></Name>
           <SE><xsl:value-of select="$SE"/></SE>
           <SpaceType>Quota</SpaceType>
           <Implementation>dCache</Implementation>
           <Version><xsl:value-of select="$version"/></Version>
           <Timestamp type="numeric"><xsl:value-of select="$now"/></Timestamp>
           <Status>Production</Status>
         </StorageElement.StorageElement>

         <StorageElementRecord.StorageElementRecord>
           <UniqueID><xsl:value-of select="$uniqId"/></UniqueID>
           <MeasurementType>logical</MeasurementType>
           <StorageType>disk</StorageType>
           <TotalSpace><xsl:value-of select="$totalSpace"/></TotalSpace>
           <FreeSpace><xsl:value-of select="$freeSpace"/></FreeSpace>
           <UsedSpace><xsl:value-of select="$usedSpace"/></UsedSpace>
         </StorageElementRecord.StorageElementRecord>

     </xsl:if>
  </xsl:for-each>

</xsl:for-each>

</array>
</setArray>
</Result>

</xsl:template>

</xsl:stylesheet>
