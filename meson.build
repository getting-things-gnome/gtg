project('gtg',
  version: '0.6.0',
  meson_version: '>= 0.51.0'
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
dbusservicedir = datadir / 'dbus-1' / 'services'
icondir = datadir / 'icons'
pythondir = python3.get_path('purelib')
rdnn_name = 'org.gnome.GTG'
application_id = rdnn_name

if get_option('profile') == 'development'
  application_id = rdnn_name + 'Devel'
endif

bin_config = configuration_data()
bin_config.set('local_build', 'False')
bin_config.set('pythondir', pythondir)
bin_config.set('localedir', datadir / 'locale')
bin_config.set('APP_ID', application_id)
bin_config.set('bindir', bindir)

local_config = configuration_data()
local_config.set('local_build', 'True')
local_config.set('pythondir', meson.source_root())
local_config.set('localedir', meson.source_root() / 'po')
local_config.set('APP_ID', application_id)


# Wrapper to launch gtg with non-/usr prefix install PYTHONPATH
wrapper_config = configuration_data()
wrapper_config.set('python_installdir', python3.get_install_dir(pure: true))
configure_file(
  input: 'prefix-gtg.sh.in',
  output: 'prefix-gtg.sh',
  configuration: wrapper_config,
)

subdir('GTG')
subdir('data')
subdir('po')
subdir('docs')
