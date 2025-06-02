gtg_plugin_sources = [
  '__init__.py',
]

python3.install_sources(gtg_plugin_sources, subdir: 'GTG' / 'plugins', pure: true)
plugin_install_dir = python3.get_install_dir(subdir: 'GTG' / 'plugins', pure: true)

gtg_plugins = [
  'export',
  'send-email',
  'untouched-tasks',
  'urgency-color',
  'hamster',
  'dev_console',
]

foreach plugin : gtg_plugins
  i18n.merge_file(
    input: plugin + '.gtg-plugin.desktop', # Big hack to make xgettext detect
    output: plugin + '.gtg-plugin',
    po_dir: meson.source_root() / 'po',
    install: true,
    install_dir: plugin_install_dir,
    type: 'desktop',
    args: ['--keyword=name', '--keyword=short-description', '--keyword=description'],
    build_by_default: true
  )
  subdir(plugin.underscorify())
endforeach
