project('gtg',
  version: '0.4.0',
  meson_version: '>= 0.49.0'
)

i18n = import('i18n')
gnome = import('gnome')
pymod = import('python')
python3 = pymod.find_installation('python3')

if not python3.found()
  error('python3 installation not found')
endif

prefix = get_option('prefix')

bindir = prefix / get_option('bindir')
datadir = prefix / get_option('datadir')

appdatadir = datadir / 'metainfo'
desktopdir = datadir / 'applications'
icondir = datadir / 'icons'
servicedir = datadir / 'dbus-1' / 'services'
pythondir = python3.get_path('purelib')

bin_config = configuration_data()
bin_config.set('local_build', 'False')
bin_config.set('pythondir', pythondir)

local_config = configuration_data()
local_config.set('local_build', 'True')
local_config.set('pythondir', meson.source_root())

subdir('GTG')
subdir('data')
subdir('po')
subdir('docs')
