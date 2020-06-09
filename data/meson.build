i18n.merge_file(
  input: configure_file(
    output: rdnn_name + '.appdata.xml.in',
    input: rdnn_name + '.appdata.xml.in.in',
    configuration: bin_config),
  output: application_id + '.appdata.xml',
  po_dir: meson.source_root() / 'po',
  install: true,
  install_dir: appdatadir,
)

i18n.merge_file(
  input: configure_file(
    output: rdnn_name + '.desktop.in',
    input: rdnn_name + '.desktop.in.in',
    configuration: bin_config),
  output: application_id + '.desktop',
  po_dir: meson.source_root() / 'po',
  install: true,
  install_dir: desktopdir,
  type: 'desktop'
)

subdir('icons')
