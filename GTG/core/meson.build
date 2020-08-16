# Find the version number and put it in info.py.
# Use git --describe if available.

git = find_program('git', required : false, disabler : true)
git_description = run_command(git, 'describe', '--dirty')

if not git.found() or git_description.returncode() != 0
  version = meson.project_version()
else
  version = git_description.stdout().strip()
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
  'datastore.py',
  'dates.py',
  'dirs.py',
  'firstrun_tasks.py',
  'interruptible.py',
  'keyring.py',
  'networkmanager.py',
  'requester.py',
  'search.py',
  'tag.py',
  'task.py',
  'xml.py',
  'timer.py',
  'treefactory.py',
  'twokeydict.py',
  'urlregex.py',
  'watchdog.py',
  'versioning.py',
]

gtg_core_plugin_sources = [
  'plugins/__init__.py',
  'plugins/api.py',
  'plugins/engine.py',
]

python3.install_sources(gtg_core_sources, subdir: 'GTG' / 'core', pure: true)
python3.install_sources(gtg_core_plugin_sources, subdir: 'GTG' / 'core' / 'plugins', pure: true)
