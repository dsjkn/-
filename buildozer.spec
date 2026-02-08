[app]

# (str) Title of your application
title = 养基宝

# (str) Package name
package.name = fundmanager

# (str) Package domain (needed for android/ios packaging)
package.domain = org.fund

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,images/*

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests,bin

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.png

# (str) Application versioning (method 1)
version = 1.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,matplotlib,pandas,numpy,akshare,requests

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy

# (list) Garden requirements
garden_requirements = matplotlib

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, portrait, all)
orientation = portrait

# (list) List of service to declare
services = 



#
# OSX Specific
#

#
# author = © Copyright Info



#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolchain)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray, 
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy, 
# olive, purple, silver, teal.
#android.presplash_color = #FFFFFF

# (string) Presplash animation using Lottie format. 
# see https://lottiefiles.com/ for examples and https://airbnb.design/lottie/ 
# for general documentation. 
# Lottie files can be created using various tools, like Adobe After Effect or Synfig.
#android.presplash_lottie = %(source.dir)s/data/presplash.lottie

# (str) Adaptive icon of the application (used if Android API level is 26+ at runtime)
#icon.adaptive_foreground.filename = %(source.dir)s/data/icon_fg.png
#icon.adaptive_background.filename = %(source.dir)s/data/icon_bg.png

# (list) Permissions
android.permissions = INTERNET

# (list) features (adds uses-feature -tags to manifest)
#android.features = android.hardware.usb.host

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 33

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use. This is the minimum API your app will support, it should usually match android.minapi.
android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_dir = 

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_dir = 

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_dir = 

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
# android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when first running
# buildozer. 
# android.accept_sdk_license = False

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, default is ok for Kivy-based app
# android.apptheme = @android:style/Theme.Holo.Light

# (list) Pattern to whitelist for the whole project
#android.whitelist = 

# (str) Path to a custom whitelist file
#android.whitelist_src = 

# (str) Path to a custom blacklist file
#android.blacklist_src = 

# (list) List of Java .jar files to add to the libs so that pyjnius can access
# their classes. Don't add jars that you do not need, since extra jars can slow
# down the build process.
#android.add_jars = foo.jar,bar.jar

# (list) List of Java files to add to the android project (can be java or a
# directory containing the files)
#android.add_src = 

# (list) Android AAR archives to add (currently works only with sdl2_gradle
# bootstrap)
#android.add_aars = 

# (list) Gradle dependencies to add (currently works only with sdl2_gradle
# bootstrap)
#android.gradle_dependencies = 

# (list) add java compile options
# this can for example be necessary if you're using the androidx support library
# see https://developer.android.com/studio/write/java8-support for further information
# android.add_compile_options = "-source 1.8", "-target 1.8"

# (list) Gradle repositories to add {can be necessary for some android.gradle_dependencies}
# please enclose in double quotes
# android.gradle_repositories = "maven { url 'https://kotlin.bintray.com/ktor' }", "maven { url 'https://jitpack.io' }"

# (list) packaging options to add
# see https://google.github.io/android-gradle-dsl/current/com.android.build.gradle.internal.dsl.PackagingOptions.html
# can be necessary to solve conflicts in gradle
# android.add_packaging_options = exclude 'META-INF/*.kotlin_module'

# (list) Java classes to add as activities to the manifest.
#android.add_activities = com.example.ExampleActivity

# (str) OUYA Console category. Should be one of GAME or APP
# If you leave this blank, OUYA support will not be enabled
#android.ouya.category = GAME

# (str) Filename of OUYA Console icon. It must be a 732x412 png image.
#android.ouya.icon.filename = %(source.dir)s/data/ouya_icon.png

# (str) XML file to include as an intent filters in <activity> tag
#android.manifest.intent_filters = 

# (str) launchMode to set for the main activity
#android.manifest.launch_mode = standard

# (list) Android additional libraries to copy into libs/armeabi
#android.add_libs_armeabi = libs/android/*.so
#android.add_libs_armeabi_v7a = libs/android-v7/*.so
#android.add_libs_arm64_v8a = libs/android-v8/*.so
#android.add_libs_x86 = libs/android-x86/*.so
#android.add_libs_mips = libs/android-mips/*.so

# (bool) Indicate whether the screen should stay on
# Don't forget to add the WAKE_LOCK permission if you set this to True
#android.wakelock = False

# (list) Android application meta-data to set (key=value format)
#android.meta_data = 

# (list) Android library project to add (will be added in the
# project.properties automatically.)
#android.library_references = 

# (list) Android shared libraries which will be added to AndroidManifest.xml using <uses-library> tag
#android.uses_library = 

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.arch = armeabi-v7a,arm64-v8a

# (int) overrides automatic versionCode computation (used in build.gradle)
# this is not the same as app.version.
# android.numeric_version = 1

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) Android backup scheme to use (see official documentation)
android.backup_rule = app

# (str) XML file for custom backup rules (see official documentation)
# android.backup_rules = res/xml/backup_rules.xml

#
# iOS specific
#

# (str) Path to a custom kivy-ios folder
#ios.kivy_ios_dir = ../kivy-ios
# Alternately, specify the URL and branch of a git checkout:
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
#ios.kivy_ios_branch = master

# (str) Name of the certificate to use for signing the debug version
# Get a list of available identities: buildozer ios list_identities
#ios.codesign.debug = "iPhone Developer: <lastname> <firstname> (<hexstring>)"

# (str) Name of the certificate to use for signing the release version
#ios.codesign.release = %(ios.codesign.debug)s


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
# bin_dir = ./bin

# (list) List of items to include in the zipfile when packaging the app for release
# include_in_release = buildozer.spec

# (list) List of items to exclude from the zipfile when packaging the app for release
# exclude_from_release = 

# (str) The rest of the section contains other settings mainly used by the tools

# (str) Base directory for android builds
# android.build_dir = ./build
# (str) Base directory for ios builds
# ios.build_dir = ./build
# (str) Base directory for macos builds
# macos.build_dir = ./build

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
# sdk_dir = 

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
# ndk_dir = 

# (str) Android SDK version to use
# sdk = 24

# (str) Android NDK version to use
# ndk = 17

# (int) Number of parallel builds
# android.concurrent_build = 4

# (bool) Use --use-sdk-wrapper (if set to True, uses javac instead of dx)
# android.use_sdk_wrapper = True

# (str) Path to Ant binary, would be automatically downloaded if not specified
# ant_bin = 

# (str) Path to Gradle binary, will be automatically downloaded if not specified
# gradle_bin = 

# (str) python-for-android branch to use, defaults to master
# p4a.branch = master

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
# p4a.source_dir = 

# (str) The directory in which python-for-android should look for your own build recipes (if any)
# p4a.local_recipes = 

# (str) Filename of Python distribution to use for building recipes
# p4a.python_dist = 

# (str) First requirement to install (overrides default order)
# p4a.first = 

# (str) Directory containing the stlport binaries 
# p4a.stlport_dir = 

# (bool) If True, then use the actual dependency names instead of the recipe names to determine whether the dependency needs to be built
# p4a.ignore_recipes = False

# (str) Order to build recipes
# p4a.build_order = 

# (list) A list of recipes to be skipped during the build process
# p4a.skip_recipes = 

# (bool) If True, then p4a will check for updates than build the distribution
# p4a.check_updates = True

# (bool) If True, then p4a will try to update the Android SDK
# p4a.update_sdk = True

# (str) Log filters to use when running python-for-android
# p4a.logcat_filters = *:S python:D

# (bool) If True, then use a custom NDK
# android.custom_ndk = 

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# p4a.arch = armeabi-v7a

# (str) The OSX arch to build for, choices: x86_64, arm64
# macos.arch = x86_64

# (int) The number of jobs to run concurrently (overrides default)# macos.cpu_count = 4

# (bool) If True, then use the lld linker, this makes builds faster
# android.use_lld = False

# (bool) If True, then enable rust support
# android.rust_support = False

# (bool) If True, then disable the gradle daemon
# android.no_gradle_daemon = False

# (bool) If True, then use the docker build
# docker = False

# (str) The default docker image to use
# docker_image = kivy/buildozer

# (list) The tags of the docker image to use (latest and a specific versioned tag)
# docker_image_tags = latest,3.1.0

# (str) The docker container name
# docker_container_name = buildozer

# (list) Additional arguments to pass to the docker run command
# docker_run_args = --rm

# (bool) If True, then clean the build area
# android.clean_build = False

# (str) The default command to run when invoking docker
# docker_command = docker

# (str) Additional environment variables to pass to the docker container
# docker_env = []

# (bool) If True, then use a virtualenv
# virtualenv = False

# (str) The path to the virtualenv directory
# virtualenv_path = venv

# (str) The Python interpreter to use inside the virtualenv
# virtualenv_python = python3

# (bool) If True, then create a new virtualenv every time
# virtualenv_new = False

# (bool) If True, then use the system's pip
# virtualenv_system_site_packages = False

# (str) The path to the Python interpreter to use for buildozer itself
# buildozer_python = python3

# (str) The path to the Python interpreter to use for p4a
# p4a.python = python3

# (str) The path to the Java JDK to use
# java_home = 

# (bool) If True, then use the system's Java
# use_system_java = False

# (str) The path to the Android SDK to use
# sdk_path = 

# (str) The path to the Android NDK to use
# ndk_path = 

# (str) The path to the Android SDK tools to use
# sdk_tools_path = 

# (str) The path to the Android platform tools to use
# platform_tools_path = 

# (str) The path to the Android build tools to use
# build_tools_path = 

# (str) The path to the Android emulator to use
# emulator_path = 

# (str) The path to the Android adb to use
# adb_path = 

# (str) The path to the Android fastboot to use
# fastboot_path = 

# (str) The path to the Android dx to use
# dx_path = 

# (str) The path to the Android aapt to use
# aapt_path = 

# (str) The path to the Android zipalign to use
# zipalign_path = 

# (str) The path to the Android apksigner to use
# apksigner_path = 

# (str) The path to the Android jarsigner to use
# jarsigner_path = 

# (str) The path to the Android keytool to use
# keytool_path = 

# (str) The path to the Android ant to use
# ant_path = 

# (str) The path to the Android gradle to use
# gradle_path = 

# (str) The path to the Android maven to use
# maven_path = 

# (str) The path to the Android protobuf to use
# protoc_path = 

# (str) The path to the Android ninja to use
# ninja_path = 

# (str) The path to the Android cmake to use
# cmake_path = 

# (str) The path to the Android ndk-build to use
# ndk_build_path = 

# (str) The path to the Android ndk-gdb to use
# ndk_gdb_path = 

# (str) The path to the Android ndk-stack to use
# ndk_stack_path = 

# (str) The path to the Android ndk-which to use
# ndk_which_path = 

# (str) The path to the Android llvm-addr2line to use
# llvm_addr2line_path = 

# (str) The path to the Android llvm-dwarfdump to use
# llvm_dwarfdump_path = 

# (str) The path to the Android llvm-objcopy to use
# llvm_objcopy_path = 

# (str) The path to the Android llvm-objdump to use
# llvm_objdump_path = 

# (str) The path to the Android llvm-readelf to use
# llvm_readelf_path = 

# (str) The path to the Android llvm-size to use
# llvm_size_path = 

# (str) The path to the Android llvm-strings to use
# llvm_strings_path = 

# (str) The path to the Android llvm-strip to use
# llvm_strip_path = 

# (str) The path to the Android clang to use
# clang_path = 

# (str) The path to the Android clang++ to use
# clangxx_path = 

# (str) The path to the Android gcc to use
# gcc_path = 

# (str) The path to the Android g++ to use
# gxx_path = 

# (str) The path to the Android as to use
# as_path = 

# (str) The path to the Android ld to use
# ld_path = 

# (str) The path to the Android ar to use
# ar_path = 

# (str) The path to the Android ranlib to use
# ranlib_path = 

# (str) The path to the Android nm to use
# nm_path = 

# (str) The path to the Android strip to use
# strip_path = 

# (str) The path to the Android objdump to use
# objdump_path = 

# (str) The path to the Android readelf to use
# readelf_path = 

# (str) The path to the Android addr2line to use
# addr2line_path = 

# (str) The path to the Android size to use
# size_path = 

# (str) The path to the Android strings to use
# strings_path = 

# (str) The path to the Android dwarfdump to use
# dwarfdump_path = 

# (str) The path to the Android objcopy to use
# objcopy_path = 

# (str) The path to the Android objdump to use
# objdump_path = 

# (str) The path to the Android readelf to use
# readelf_path = 

# (str) The path to the Android size to use
# size_path = 

# (str) The path to the Android strings to use
# strings_path = 

# (str) The path to the Android strip to use
# strip_path = 

# (str) The path to the Android nm to use
# nm_path = 

# (str) The path to the Android ranlib to use
# ranlib_path = 

# (str) The path to the Android ar to use
# ar_path = 

# (str) The path to the Android ld to use
# ld_path = 

# (str) The path to the Android as to use
# as_path = 

# (str) The path to the Android g++ to use
# gxx_path = 

# (str) The path to the Android gcc to use
# gcc_path = 

# (str) The path to the Android clang++ to use
# clangxx_path = 

# (str) The path to the Android clang to use
# clang_path = 

# (str) The path to the Android llvm-strip to use
# llvm_strip_path = 

# (str) The path to the Android llvm-strings to use
# llvm_strings_path = 

# (str) The path to the Android llvm-size to use
# llvm_size_path = 

# (str) The path to the Android llvm-readelf to use
# llvm_readelf_path = 

# (str) The path to the Android llvm-objdump to use
# llvm_objdump_path = 

# (str) The path to the Android llvm-objcopy to use
# llvm_objcopy_path = 

# (str) The path to the Android llvm-dwarfdump to use
# llvm_dwarfdump_path = 

# (str) The path to the Android llvm-addr2line to use
# llvm_addr2line_path = 

# (str) The path to the Android ndk-which to use
# ndk_which_path = 

# (str) The path to the Android ndk-stack to use
# ndk_stack_path = 

# (str) The path to the Android ndk-gdb to use
# ndk_gdb_path = 

# (str) The path to the Android ndk-build to use
# ndk_build_path = 

# (str) The path to the Android cmake to use
# cmake_path = 

# (str) The path to the Android ninja to use
# ninja_path = 

# (str) The path to the Android protobuf to use
# protoc_path = 

# (str) The path to the Android maven to use
# maven_path = 

# (str) The path to the Android gradle to use
# gradle_path = 

# (str) The path to the Android ant to use
# ant_path = 

# (str) The path to the Android keytool to use
# keytool_path = 

# (str) The path to the Android jarsigner to use
# jarsigner_path = 

# (str) The path to the Android apksigner to use
# apksigner_path = 

# (str) The path to the Android zipalign to use
# zipalign_path = 

# (str) The path to the Android aapt to use
# aapt_path = 

# (str) The path to the Android dx to use
# dx_path = 

# (str) The path to the Android adb to use
# adb_path = 

# (str) The path to the Android fastboot to use
# fastboot_path = 

# (str) The path to the Android emulator to use
# emulator_path = 

# (str) The path to the Android build tools to use
# build_tools_path = 

# (str) The path to the Android platform tools to use
# platform_tools_path = 

# (str) The path to the Android SDK tools to use
# sdk_tools_path = 

# (str) The path to the Android NDK to use
# ndk_path = 

# (str) The path to the Android SDK to use
# sdk_path = 

# (str) The path to the Java JDK to use
# java_home = 

# (bool) If True, then use the system's Java
# use_system_java = False

# (str) The path to the Python interpreter to use for p4a
# p4a.python = python3

# (str) The path to the Python interpreter to use for buildozer itself
# buildozer_python = python3

# (bool) If True, then use the system's pip
# virtualenv_system_site_packages = False

# (bool) If True, then create a new virtualenv every time
# virtualenv_new = False

# (str) The path to the virtualenv directory
# virtualenv_path = venv

# (bool) If True, then use a virtualenv
# virtualenv = False

# (str) Additional environment variables to pass to the docker container
# docker_env = []

# (list) Additional arguments to pass to the docker run command
# docker_run_args = --rm

# (str) The docker container name
# docker_container_name = buildozer

# (list) The tags of the docker image to use (latest and a specific versioned tag)
# docker_image_tags = latest,3.1.0

# (str) The default docker image to use
# docker_image = kivy/buildozer

# (bool) If True, then use the docker build
# docker = False

# (bool) If True, then disable the gradle daemon
# android.no_gradle_daemon = False

# (bool) If True, then enable rust support
# android.rust_support = False

# (bool) If True, then use the lld linker, this makes builds faster
# android.use_lld = False

# (int) The number of jobs to run concurrently (overrides default)# macos.cpu_count = 4

# (str) The OSX arch to build for, choices: x86_64, arm64
# macos.arch = x86_64

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# p4a.arch = armeabi-v7a

# (str) Log filters to use when running python-for-android
# p4a.logcat_filters = *:S python:D

# (bool) If True, then p4a will try to update the Android SDK
# p4a.update_sdk = True

# (bool) If True, then p4a will check for updates than build the distribution
# p4a.check_updates = True

# (list) A list of recipes to be skipped during the build process
# p4a.skip_recipes = 

# (str) Order to build recipes
# p4a.build_order = 

# (bool) If True, then use the actual dependency names instead of the recipe names to
determine whether the dependency needs to be built
# p4a.ignore_recipes = False

# (str) Directory containing the stlport binaries 
# p4a.stlport_dir = 

# (str) First requirement to install (overrides default order)
# p4a.first = 

# (str) Filename of Python distribution to use for building recipes
# p4a.python_dist = 

# (str) The directory in which python-for-android should look for your own build recipes (if any)
# p4a.local_recipes = 

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
# p4a.source_dir = 

# (str) python-for-android branch to use, defaults to master
# p4a.branch = master

# (str) Path to Gradle binary, will be automatically downloaded if not specified
# gradle_bin = 

# (str) Path to Ant binary, would be automatically downloaded if not specified
# ant_bin = 

# (bool) Use --use-sdk-wrapper (if set to True, uses javac instead of dx)
# android.use_sdk_wrapper = True

# (int) Number of parallel builds
# android.concurrent_build = 4

# (str) Android NDK version to use
# ndk = 17

# (str) Android SDK version to use
# sdk = 24

# (str) NDK directory (if empty, it will be automatically downloaded.)
# ndk_dir = 

# (str) SDK directory (if empty, it will be automatically downloaded.)
# sdk_dir = 

# (str) Base directory for macos builds
# macos.build_dir = ./build

# (str) Base directory for ios builds
# ios.build_dir = ./build

# (str) Base directory for android builds
# android.build_dir = ./build

# (list) List of items to exclude from the zipfile when packaging the app for release
# exclude_from_release = 

# (list) List of items to include in the zipfile when packaging the app for release
# include_in_release = buildozer.spec

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
# bin_dir = ./bin

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer


