import optparse, os, pickle

config = {'charity':False,
          'propagate_factor':2,
          'accept_latency':2000}

def setup():
  parser = optparse.OptionParser()
  parser.add_option('-c',
                    '--charity',
                    dest='charity',
                    default=None,
                    action="store_true",
                    help='Sets whether you accept rewardless bounties')
  parser.add_option('-l',
                    '--latency',
                    dest='accept_latency',
                    default=None,
                    help='Maximum acceptable latency from a server')
  parser.add_option('-f',
                    '--propagation-factor',
                    dest='propagate_factor',
                    default=None,
                    help='Minimum funds:reward ratio you\'ll propagate bounties at')        
  (options, args) = parser.parse_args()

  print "options parsed"
  overrides = options.__dict__
  
  if os.path.exists("settings.conf"):
    config.update(pickle.load(open("settings.conf","r")))
    print overrides
    print config
  else:
    pickle.dump(config,open("settings.conf","w"))
  kill = []
  for key in overrides:
    if overrides.get(key) is None:
      kill += [key]
  for key in kill:
    overrides.pop(key)
  config.update(overrides)
