import psycopg2
import sys
import json
import os
import math
import matplotlib.pyplot as plt

def identifyBackgroundStations(conn):
    bgStations = set()
    
    with conn.cursor() as cur:
        cur.execute("select station,seen,ssid from probe order by station, seen, ssid;")
        
        oldStation = None
        oldSsid = None
        sightings = list()
        
        for row in cur:
            station, seen, ssid = row
            
            if oldStation != station or oldSsid != ssid:
                #Only consider a station background if it occurs for more than an hour
                if len(sightings) > 60/5:
                    diffSightings = [(sightings[i+1] - sightings[i]).total_seconds() for i in xrange(0,len(sightings)-1)]
                    averageTimeBetweenSightings = sum(diffSightings)/float(len(diffSightings))
                    
                    #Use sample standard deviation since it is assumed some observations
                    #are missed
                    stddev = math.sqrt( 1/ float(len(diffSightings)-1) * sum(math.pow(i - averageTimeBetweenSightings,2.0) for i in diffSightings) )
                    stddevmean = stddev/math.sqrt(len(diffSightings))
                    
                    cl = 1.96
                    lower = averageTimeBetweenSightings - cl*stddevmean
                    upper = averageTimeBetweenSightings + cl*stddevmean
                    
                    expectedValue = 5*60
                    if expectedValue > lower and expectedValue < upper:
                        bgStations.add(oldStation)
                        print '%i - %i:%f pm %f' %(oldStation, len(sightings),averageTimeBetweenSightings,stddevmean)
                    
                sightings = list()
            sightings.append(seen)
            oldStation = station
            oldSsid = ssid
        
        conn.rollback()
        
    return bgStations
    

if __name__ == "__main__":

    with open(sys.argv[1]) as fin:
        conf = json.load(fin)			
	
	conn = psycopg2.connect(**conf)
    numrows = 0
    singles = 0
    cnts = []
    
    with conn.cursor() as cur:
        cur.execute("Select count(1) from probe group by station")
        for row in cur:
            cnt, = row
            if cnt == 1:
                singles += 1    
            numrows += 1
            cnts.append(cnt)
                
        conn.rollback()
    print 'Unique Stations %i' % numrows
    print 'Stations observed more than once %i' % (numrows - singles)
    plt.pie([numrows-singles,singles],labels=['More Than Once','Exactly Once'],colors=['yellowgreen','lightskyblue'],shadow=True,autopct='%1.1f%%',startangle=120.0)
    plt.axis('equal')
    plt.title('Fraction of stations sighted more than once')
    plt.savefig('stations_sighted.png')
    
    plt.close()
    
    bgStations = identifyBackgroundStations(conn)
    print 'Found %d background stations' % len(bgStations)
    
    weekdaycnts = [0]*7
    hrdaycnts = [0]*24
    discard = 0
    total = 0
    with conn.cursor() as cur:
        cur.execute("Select station,seen from probe")
        
        for row in cur:
            total += 1
            station,seen = row
            if station in bgStations:
                discard += 1
                continue
            weekdaycnts[seen.weekday()] += 1
            hrdaycnts[seen.hour] += 1
        conn.rollback()
        
    print 'Discarded %i values, %f%%' % (discard,100*discard/float(total),)
    weekdays = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    index = range(len(weekdaycnts))
    bar_width = 0.25
    plt.bar(index,weekdaycnts,bar_width)
    plt.xticks(index, weekdays)
    plt.xlabel('Day of Week')
    plt.ylabel('Probes Captured')
    plt.title('Probes Captured Per Day of Week')
    plt.savefig('day_of_week.png')
    plt.close()
    
    
    index = range(len(hrdaycnts))
    plt.bar(index,hrdaycnts,bar_width)
    plt.xlabel('Hour of Day')
    plt.ylabel('Probes Captured')
    plt.title('Probes Captured Per Hour of Day')
    plt.xticks(index, [str(i+1) for i in index])
    plt.savefig('hr_of_day.png')
    
        
        
    
    
    
        
    
