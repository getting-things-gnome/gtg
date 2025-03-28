gtg_gtk_sources = [
  '__init__.py',
  'action_row.py',
  'application.py',
  'colors.py',
  'errorhandler.py',
  'general_preferences.py',
  'plugins.py',
  'preferences.py',
  'tag_completion.py',
]

gtg_backend_sources = [
  'backends/__init__.py',
  'backends/addpanel.py',
  'backends/backendscombo.py',
  'backends/backendstree.py',
  'backends/configurepanel.py',
]

gtg_backend_parameters_ui_sources = [
  'backends/parameters_ui/__init__.py',
  'backends/parameters_ui/checkbox.py',
  'backends/parameters_ui/import_tags.py',
  'backends/parameters_ui/password.py',
  'backends/parameters_ui/path.py',
  'backends/parameters_ui/period.py',
  'backends/parameters_ui/text.py',
]

gtg_browser_sources = [
  'browser/__init__.py',
  'browser/adaptive_button.py',
  'browser/backend_infobar.py',
  'browser/delete_tag.py',
  'browser/delete_task.py',
  'browser/main_window.py',
  'browser/modify_tags.py',
  'browser/simple_color_selector.py',
  'browser/sidebar_context_menu.py',
  'browser/search_editor.py',
  'browser/tag_editor.py',
  'browser/quick_add.py',
  'browser/sidebar.py',
  'browser/tag_pill.py',
  'browser/task_pane.py',
]

gtg_data_sources = [
  'data/action_row.ui',
  'data/backends.ui',
  'data/calendar.ui',
  'data/context_menus.ui',
  'data/general_preferences.ui',
  'data/main_window.ui',
  'data/modify_tags.ui',
  'data/plugins.ui',
  'data/preferences.ui',
  'data/style.css',
  'data/tag_editor.ui',
  'data/search_editor.ui',
  'data/task_editor.ui',
  'data/recurring_menu.ui'
]

gtg_editor_sources = [
  'editor/__init__.py',
  'editor/calendar.py',
  'editor/editor.py',
  'editor/taskview.py',
  'editor/recurring_menu.py',
  'editor/text_tags.py',
]

python3.install_sources(gtg_gtk_sources, subdir: 'GTG' / 'gtk', pure: true)
python3.install_sources(gtg_backend_sources, subdir: 'GTG' / 'gtk' / 'backends', pure: true)
python3.install_sources(gtg_backend_parameters_ui_sources, subdir: 'GTG' / 'gtk' / 'backends' / 'parameters_ui', pure: true)
python3.install_sources(gtg_browser_sources, subdir: 'GTG' / 'gtk' / 'browser', pure: true)
python3.install_sources(gtg_data_sources, subdir: 'GTG' / 'gtk' / 'data', pure: true)
python3.install_sources(gtg_editor_sources, subdir: 'GTG' / 'gtk' / 'editor', pure: true)
