gtg_sources = [
  '__init__.py'
]

# The explicit `pure: true` can go away here and other files once we rely
# on new enough meson to guarantee the default is pure as documented
# https://github.com/mesonbuild/meson/pull/6848
python3.install_sources(gtg_sources, subdir: 'GTG', pure: true)

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
