gtg_sources = [
  '__init__.py'
]

python3.install_sources(gtg_sources, subdir: 'GTG')

configure_file(
  input: 'gtg.in',
  output: 'gtg',
  configuration: bin_config,
  install_dir: bindir
)
configure_file(
  input: 'gtg.in',
  output: 'local-gtg',
  configuration: local_config,
)

subdir('core')
subdir('backends')
subdir('gtk')
subdir('plugins')
