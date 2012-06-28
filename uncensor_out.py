from twisted.web import resource
from db_helper import DbHelper
from config import Config
import json, re

class UncensorOutResource(resource.Resource):
  isLeaf = True
  pathFromRoot = '/service/uncensor_domains'

  def render_GET(self, request):
    macdb = DbHelper()
    
    ua = request.requestHeaders.getRawHeaders('User-Agent')
    if ua != None:
      ua = ua[0]
      x2 = ua.split()[1]
      os = (x2.find('Windows') != -1) ? 'win' : ((x2.find('Mac OS') != -1) ? 'mac' : None)

      matchObj = re.match( r'BitPop/(\d+\.\d+\.\d+\.\d+)', ua) # get version

      if matchObj and os:
        macdb.stats_add(matchObj.groups(1), os)

    res = macdb.uncensor_fetch_all()
    macdb.cleanup()
    
    request.setHeader('Content-Type', 'application/json')
    
    return json.dumps(res)
