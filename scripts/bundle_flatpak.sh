#!/usr/bin/env bash

# This little script generates a flatpak file and installs it
# after removing the previous version.

echo -e "GTG's Awesome Flatpak Generator"
echo -e "-----------------------------------------------------------------------"
echo -e "\nThis script will create a flatpak file and install it."

PS3='Please enter your choice: '
options=("Stable" "Development")
select opt in "${options[@]}"

do
    case $opt in
        "Stable")
            appid="org.gnome.GTG"
            manifest="org.gnome.GTG-stable.json"
            repo="repo-stable"
            app="app-stable"
            break
            ;;
        "Development")
            appid="org.gnome.GTGDevel"
            manifest="org.gnome.GTG.json"
            repo="repo"
            app="app"
            break
            ;;
    *);;
    esac
done


cd ../flatpak || exit

mkdir -p tmp
mkdir -p bundles

flatpak-builder --repo=tmp/$repo --force-clean tmp/$app "$manifest"
flatpak build-bundle tmp/$repo bundles/$appid.flatpak $appid
flatpak uninstall -y --user $appid
flatpak install -y --user bundles/$appid.flatpak

echo -e "\nAll done. You can find the flatpak file in ../flatpak/bundles"
