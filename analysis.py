import psycopg2
import sys
import json
import os
import math
import matplotlib.pyplot as plt

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
    
    timeBetweenSightings = []
    backgroundStations = []
    with conn.cursor() as cur:
        cur.execute("select station,seen from probe order by station, seen;")
        
        oldStation = None
        sightings = []
        
        for row in cur:
            station, seen = row
            
            if oldStation != station:
                if len(sightings) > 1:
                    diffSightings = [(sightings[i+1] - sightings[i]).total_seconds() for i in xrange(0,len(sightings)-1)]
                    averageTimeBetweenSightings = sum(diffSightings)/float(len(diffSightings))
                    if not averageTimeBetweenSightings < 10*60:
                        timeBetweenSightings.append(averageTimeBetweenSightings)
                sightings = []
            sightings.append(seen)
            oldStation = station
        
        conn.rollback()
    plt.hist(timeBetweenSightings)
    plt.title('Average Time Between Sightings In Seconds Per Station')
    plt.savefig('time_between_sightings.png')
    
    plt.close()
    
    weekdaycnts = [0]*7
    hrdaycnts = [0]*24
    with conn.cursor() as cur:
        cur.execute("Select seen from probe")
        for row in cur:
            seen, = row
            weekdaycnts[seen.weekday()] += 1
            hrdaycnts[seen.hour] += 1
        conn.rollback()
        
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
    
        
        
    
    
    
        
    
