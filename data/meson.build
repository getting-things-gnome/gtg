appdata_file = 'org.gnome.GTG.appdata.xml'
install_data(appdata_file, install_dir: appdatadir)

desktop_file = 'org.gnome.GTG.desktop'
i18n.merge_file(desktop_file,
  input: desktop_file + '.in',
  output: desktop_file,
  po_dir: meson.source_root() / 'po',
  install: true,
  install_dir: desktopdir,
  type: 'desktop'
)

service_file = 'org.gnome.GTG.service'
install_data(service_file, install_dir: servicedir)

subdir('icons')
