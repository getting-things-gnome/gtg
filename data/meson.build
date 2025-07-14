i18n.merge_file(
  input: configure_file(
    output: rdnn_name + '.metainfo.xml.in',
    input: rdnn_name + '.metainfo.xml.in.in',
    configuration: bin_config),
  output: application_id + '.metainfo.xml',
  po_dir: meson.source_root() / 'po',
  install: true,
  install_dir: metainfodir,
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

service_config = configuration_data()
service_config.set('APP_ID', application_id)
service_config.set('bindir', bindir)

configure_file(
  input: rdnn_name + '.service.in',
  output: application_id + '.service',
  configuration: service_config,
  install: true,
  install_dir: dbusservicedir
)

subdir('icons')
