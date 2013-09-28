
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

import scapy
from scapy.all import sniff
import sys
import struct
import json
import psycopg2
import datetime
from io import open
MGMT_TYPE = 0x0
PROBE_SUBTYPE = 0x04
BEACON_SUBTYPE = 0x08

FMT_HEADER_80211 = "<HH6s6s6sH"
WLAN_MGMT_ELEMENT = "<BB"
BEACON_FIXED_PARAMETERS = "<xxxxxxxxHH"

TO_DS_BIT = 2**9
FROM_DS_BIT = 2**10

def encodeMac(s):
	return ''.join(( '%.2x' % ord(i) for i in s ))

class Handler(object):
	def __init__(self,conf):
		self.conf = conf
		self.conn = None
		
	def getDatabaseConnection(self):
	
		if self.conn == None:
			self.conn = psycopg2.connect(**conf)
			
		return self.conn
		
	def __call__(self,pkt):
		#If the packet is not a management packet ignore it
		if not pkt.type == MGMT_TYPE:
			return	
		
		#Extract the payload from the packet
		payload = buffer(str(pkt.payload))
		#Carve out just the header
		headerSize = struct.calcsize(FMT_HEADER_80211)
		header = payload[:headerSize]
		#unpack the header
		frameControl,dur,addr1,addr2,addr3,seq = struct.unpack(FMT_HEADER_80211,header)
		
		fromDs = (FROM_DS_BIT & frameControl) != 0
		toDs = (TO_DS_BIT & frameControl) != 0
		
		if fromDs and not toDs:
			srcAddr = addr3
		elif not  fromDs and not toDs:
			srcAddr = addr2
		elif not fromDs and toDs:
			srcAddr = addr2
		elif fromDs and toDs:
			return
		
		#Query the database to see the last time this station was seen
		conn = self.getDatabaseConnection()
		cur = conn.cursor()
		
		cur.execute("Select id,lastseen from station where mac = %s;",(encodeMac(srcAddr),))
		r = cur.fetchone()
		#If never seen, add the station to the database
		if r == None:
			cur.execute("Insert into station(mac,firstSeen,lastSeen) VALUES(%s,current_timestamp at time zone 'utc',current_timestamp at time zone 'utc') returning id;",(encodeMac(srcAddr),))
			r = cur.fetchone()
			suid = r
		#If seen, update the last seen time of the station 
		else:
			suid,lastSeen = r
			cur.execute("Update station set lastSeen = %s where id = %s",(datetime.datetime.now(),suid,))
		cur.close()
		conn.commit()
		
		#If the packet subtype is not probe or beacon ignore the rest of it
		isBeacon = pkt.subtype == BEACON_SUBTYPE
		isProbe = pkt.subtype == PROBE_SUBTYPE
		if not (isBeacon or isProbe):
			return
		
		#Extract each tag from the payload
		tags = payload[headerSize:]
		
		if isBeacon:
			tags = tags[struct.calcsize(BEACON_FIXED_PARAMETERS):]
		
		ssid = None
		while len(tags) != 0:
			#Carve out and extract the id and length of the  tag
			tagHeader = tags[0:struct.calcsize(WLAN_MGMT_ELEMENT)]
			tagId,tagLength = struct.unpack(WLAN_MGMT_ELEMENT,tagHeader)
			tags = tags[struct.calcsize(WLAN_MGMT_ELEMENT):]

			#If the tag id is for SSID and the tag length is not zero
			#then print it
			if tagId == 0 and tagLength !=0:

				ssid = tags[:tagLength]
				if isBeacon:
					verb = 'is'
				else:
					verb = 'wants'
				print '%s %s %s' % ( ''.join([ '%.2x' % ord(i) for i in srcAddr]) , verb,ssid, )
				break 
				
			tags = tags[tagLength:]
			
		if ssid != None:
			
			#Query the database to find the ssid
			cur = conn.cursor()
			cur.execute("Select id from ssid where name = %s",(ssid,))
			r = cur.fetchone()
			if r == None:
				cur.execute("Insert into ssid (name) VALUES(%s) returning id;",(ssid,))
				r = cur.fetchone()
				ssuid, = r
				cur.close()	
				conn.commit()
			else:
				ssuid, = r
				cur.close()
				conn.rollback()
			
			
			#Query the database for a beacon/probe by the station
			#if it was observed in the past 5 minutes,
			#don't add this one to the database				
			cur = conn.cursor()
			
			update = False
			if isBeacon:
				cur.execute("Select seen from beacon left join ssid on beacon.ssid=ssid.id where station = %s and ssid.id = %s order by seen desc limit 1;",(suid,ssuid,))
				r = cur.fetchone()
				
				#If no entry, then update
				if r == None:
					update = True
				else:
					seen, = r
					if (datetime.datetime.now() - seen).total_seconds() > (5*60):
						update = True
				
				if update:
					cur.execute("Insert into beacon (station,ssid,seen) VALUES(%s,%s,current_timestamp at time zone 'utc')",(suid,ssuid,))
					cur.close()
					conn.commit()
				else:
					cur.close()
					conn.rollback()
			elif isProbe:
				cur.execute("Select seen from probe left join ssid on probe.ssid=ssid.id where station = %s and ssid.id = %s order by seen desc limit 1;", (suid,ssuid,))
				r = cur.fetchone()
				
				if r == None:
					update = True
				else:
					seen, = r 
					if (datetime.datetime.now() - seen).total_seconds() > (5*60):
						update = True
					
				if update:
					cur.execute("Insert into probe(station,ssid,seen) VALUES(%s,%s,current_timestamp at time zone 'utc')",(suid,ssuid,))
					cur.close()
					conn.commit()
				else:
					cur.close()
					conn.rollback()
		
					
					
			

if __name__ == "__main__":
	iface = sys.argv[1]
	with open(sys.argv[2]) as fin:
		conf = json.load(fin)			
	
	handler = Handler(conf)				
	sniff(iface=iface,prn=handler,store=0)

	
