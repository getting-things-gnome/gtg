appdata_file = 'org.gnome.GTG.appdata.xml'
i18n.merge_file(appdata_file,
  input: appdata_file + '.in',
  output: appdata_file,
  po_dir: meson.source_root() / 'po',
  install: true,
  install_dir: appdatadir,
)

desktop_file = 'org.gnome.GTG.desktop'
i18n.merge_file(desktop_file,
  input: desktop_file + '.in',
  output: desktop_file,
  po_dir: meson.source_root() / 'po',
  install: true,
  install_dir: desktopdir,
  type: 'desktop'
)

subdir('icons')
