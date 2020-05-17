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

subdir('GTG')
subdir('data')
subdir('po')
subdir('docs')
