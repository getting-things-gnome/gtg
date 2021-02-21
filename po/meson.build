i18n.gettext('gtg',
  preset: 'glib',
  args: [
    # Used by gtg-plugin
    '--keyword=name', '--keyword=short-description', '--keyword=description'
    ]
  )

# Used because plugins require i18n.merge_file which silently does nothing when
# xgettext hasn't been found.
find_program('xgettext', required: true)
