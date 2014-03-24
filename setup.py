#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright(c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or(at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

from distutils.core import setup
from glob import glob
from subprocess import call
import os
import sys

from GTG import info


def find_packages():
    """ Generate list of all packages """
    packages = []
    for package, __, files in os.walk('GTG'):
        # Package has to have init file
        if '__init__.py' not in files:
            continue
        # Convert filepath to package name
        package = package.replace(os.path.sep, '.')
        packages.append(package)
    return packages


def find_package_data():
    """ Generate list of data files within a package """
    packages = {
        package.replace('.', os.path.sep) for package in find_packages()}
    package_data = {}

    for folder, __, files in os.walk('GTG'):
        # Find package
        closest_package = folder
        while closest_package and closest_package not in packages:
            # Try one level up
            closest_package = os.path.dirname(closest_package)

        if not closest_package:
            continue

        allowed_extensions = [
            '', '.gtg-plugin', '.png', '.svg', '.ui', '.html', '.tex', '.txt']
        is_this_package = folder == closest_package
        if not is_this_package:
            allowed_extensions.append('.py')

        for filename in files:
            ext = os.path.splitext(filename)[-1]
            if ext not in allowed_extensions:
                continue

            # Find path relative to package
            filename = os.path.join(folder, filename)
            assert filename.startswith(closest_package)
            filename = filename[len(closest_package + os.path.sep):]

            # Assign data file to package name
            package_name = closest_package.replace(os.path.sep, '.')
            if package_name in package_data:
                package_data[package_name].append(filename)
            else:
                package_data[package_name] = [filename]

    return package_data


def compile_mo_files():
    """ Compile all .po files into .mo files """
    mo_files = []
    mo_dir = os.path.join('build', 'po')
    for po_file in glob('po/*.po'):
        lang = os.path.splitext(os.path.basename(po_file))[0]
        mo_file = os.path.join(mo_dir, lang, 'gtg.mo')
        target_dir = os.path.dirname(mo_file)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        try:
            return_code = call(['msgfmt', '-o', mo_file, po_file])
        except OSError:
            sys.stderr.write(
                'Translation not available, please install gettext\n')
            break

        if return_code:
            raise Warning('Error when building locales')
            continue

        install_folder = os.path.join('share', 'locale', lang, 'LC_MESSAGES')
        mo_files.append((install_folder, [mo_file]))

    return mo_files


def find_icons(src_folder, dest_folder, allowed_extensions):
    """ Find all icons in the folder """
    data_list = []

    for folder, __, files in os.walk(src_folder):
        assert folder.startswith(src_folder)
        install_folder = dest_folder + folder[len(src_folder):]
        file_list = []
        for filename in files:
            ext = os.path.splitext(filename)[-1]
            if ext in allowed_extensions:
                filename = os.path.join(folder, filename)
                file_list.append(filename)

        if file_list:
            data_list.append((install_folder, file_list))

    return data_list


def find_user_help():
    """ Find all files for user help """
    help_files = []

    for folder, __, files in os.walk('docs/userdoc'):
        folders = folder.split(os.path.sep)[2:]
        if not folders:
            continue
        folders.insert(1, 'gtg')
        install_folder = os.path.join('share', 'help', *folders)

        help_files.append((
            install_folder,
            [os.path.join(folder, filename) for filename in files],
        ))

    return help_files


def find_data_files():
    """ Generate list of data files for installing in share folder """
    data_files = []

    # .mo files
    data_files.extend(compile_mo_files())

    # Icons
    data_files.extend(
        find_icons('data/icons', 'share/icons', ['.png', '.svg']))

    # User docs
    data_files.extend(find_user_help())

    # Generate man files and include them
    os.system('sphinx-build -b man docs/source build/docs')
    data_files.append(('share/man/man1', glob('build/docs/*.1')))

    # Misc files
    data_files.extend([
        ('share/applications', ['data/gtg.desktop']),
        ('share/appdata/', ['data/gtg.appdata.xml']),
        ('share/dbus-1/services', ['data/org.gnome.GTG.service']),
        ('share/gtg/', ['data/gtcli_bash_completion']),
    ])

    return data_files


setup(
    name='gtg',
    version=info.VERSION,
    url=info.URL,
    author='The GTG Team',
    author_email=info.EMAIL,
    description=info.SHORT_DESCRIPTION,
    packages=find_packages(),
    package_data=find_package_data(),
    scripts=['GTG/gtg', 'GTG/gtcli', 'GTG/gtg_new_task'],
    data_files=find_data_files(),
)
