'''
Created on Jul 10, 2012

@author: sean
'''

import urllib2
from urllib import urlencode
from lxml import html
from zipfile import ZipFile
from sys import stdout
from os.path import abspath

def download_noaa_data():
    values = { "startDate" : "2010-10-15",
        "endDate" : "2012-07-05",
        "minLon" : "20",
        "maxLon" : "20",
        "minLat" : "-60",
        "maxLat" : "60",
        "dataType" : "5day",
        "filterType" : "filter",
        "username" : "none",
        "phone" : "",
        "organization" : "",
        "description" : "",
        "varType" : "u,v",
    }
    
    NOAA_URL = "http://www.oscar.noaa.gov"
    
    data = urlencode(values)
    req = urllib2.Request(NOAA_URL + '/datadisplay/download.php', data)
    
    print "getting download link..."
    response = urllib2.urlopen(req)
    
    doc = html.parse(response)
    
    xpath = "/html/body//a"
    links = [elem.attrib.get('href') for elem in doc.xpath(xpath)]
    
    nc_file = [link for link in links if link.startswith('/cache/')][0]
    print "downloading file %s ... " % (nc_file,)
    
    req = urllib2.Request(NOAA_URL + nc_file)
    response = urllib2.urlopen(req)
    
    clen = int(response.headers.get('content-length')) / 1024
    print "reading %i Kb" %(clen,)
    i = 0
    with open('data.zip', 'wb') as fd:
        while 1:
            bin = response.read(1024)
            if not bin:
                break
            fd.write(bin)
            
            stdout.write('read     %5.2f%% \r' % (100. * i / clen,))
            stdout.flush()
            i += 1
        
    with ZipFile('data.zip', 'r') as zipf:
        print "extracting .. %s " %(zipf.namelist()[0],) 
        zipf.extract(zipf.namelist()[0])
    
    return abspath(zipf.namelist()[0])
    

def data_file():
    pass