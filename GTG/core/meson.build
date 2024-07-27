git = find_program('git', required : false, disabler : true)

if git.found() and get_option('profile') == 'development'
    base_version = meson.project_version()
    commit = run_command(
            ['git', 'rev-parse', '--short', 'HEAD'],
            check: true
        ).stdout().strip()
    version = base_version + '-' + commit
elif get_option('profile') == 'flatpak_snapshot'
    base_version = meson.project_version()
    date = run_command(
            ['date', '--utc', '+%Y%m%d'],
            check: true
        ).stdout().strip()
    version = base_version + '-' + date
else
    version = meson.project_version()
endif

info_config = configuration_data()
info_config.set('VCS_TAG', version)

infodir = python3.get_install_dir()
info_py = configure_file(
            input : 'info.py.in',
            output :'info.py',
            configuration: info_config,
            install : true,
            install_dir: infodir / 'GTG' / 'core')

gtg_core_sources = [
  '__init__.py',
  'borg.py',
  'clipboard.py',
  'config.py',
  'dates.py',
  'dirs.py',
  'firstrun_tasks.py',
  'interruptible.py',
  'keyring.py',
  'networkmanager.py',
  'search.py',
  'timer.py',
  'twokeydict.py',
  'urlregex.py',
  'watchdog.py',
  'versioning.py',
  'base_store.py',
  'tasks.py',
  'tags.py',
  'saved_searches.py',
  'datastore.py',
  'filters.py',
  'sorters.py',
  'system_info.py',
]

gtg_core_plugin_sources = [
  'plugins/__init__.py',
  'plugins/api.py',
  'plugins/engine.py',
]

python3.install_sources(gtg_core_sources, subdir: 'GTG' / 'core', pure: true)
python3.install_sources(gtg_core_plugin_sources, subdir: 'GTG' / 'core' / 'plugins', pure: true)
