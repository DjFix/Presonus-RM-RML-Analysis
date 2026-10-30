# Candidate integration entry point. No prebuilt archive is accepted.
include_guard(GLOBAL)
option(PRESONUS_ENABLE_UPSTREAM_CORE "Build the pinned Linux source provider" OFF)
set(PRESONUS_CORE_SOURCE_DIR "" CACHE PATH "Pinned ccl-framework checkout")
set(PRESONUS_CORE_DEPENDENCY_PREFIX "" CACHE PATH "Optional real dependency SDK prefix")
if(NOT PRESONUS_ENABLE_UPSTREAM_CORE)
  return()
endif()
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
  message(FATAL_ERROR "PRESONUS_ENABLE_UPSTREAM_CORE currently supports Linux only")
endif()
if(CMAKE_CONFIGURATION_TYPES OR NOT CMAKE_BUILD_TYPE STREQUAL "Release")
  message(FATAL_ERROR "Core provider candidate requires single-config Release")
endif()
include(ExternalProject)
find_package(PNG REQUIRED)
find_package(ZLIB REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")
find_package(CoreDNSSD REQUIRED)
set(_core_work "${CMAKE_CURRENT_BINARY_DIR}/upstream-core")
set(_core_sdk "${_core_work}/sdk")
# Imported include directories must exist during parent generation.
file(MAKE_DIRECTORY "${_core_sdk}/include/presonus-core-5")
set(_core_toolchain_args)
if(CMAKE_C_COMPILER)
  list(APPEND _core_toolchain_args "-DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}")
endif()
if(CMAKE_TOOLCHAIN_FILE)
  list(APPEND _core_toolchain_args "-DCMAKE_TOOLCHAIN_FILE:FILEPATH=${CMAKE_TOOLCHAIN_FILE}")
endif()
ExternalProject_Add(presonus_core_source_project
  SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/../native"
  BINARY_DIR "${_core_work}/build"
  STAMP_DIR "${_core_work}/stamps" TMP_DIR "${_core_work}/temp"
  INSTALL_DIR "${_core_sdk}"
  DOWNLOAD_COMMAND "" UPDATE_COMMAND ""
  CMAKE_ARGS "-DCMAKE_BUILD_TYPE:STRING=Release"
    "-DPRESONUS_CORE_SOURCE_DIR:PATH=${PRESONUS_CORE_SOURCE_DIR}"
    "-DCMAKE_INSTALL_PREFIX:PATH=<INSTALL_DIR>" "-DCMAKE_INSTALL_LIBDIR:STRING=lib"
    "-DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}"
    "-DCMAKE_PREFIX_PATH:PATH=${PRESONUS_CORE_DEPENDENCY_PREFIX}"
    "-DPNG_PNG_INCLUDE_DIR:PATH=${PNG_PNG_INCLUDE_DIR}"
    "-DPNG_LIBRARY_RELEASE:FILEPATH=${PNG_LIBRARY_RELEASE}"
    "-DCoreDNSSD_INCLUDE_DIR:PATH=${CoreDNSSD_INCLUDE_DIR}"
    "-DCoreDNSSD_LIBRARY:FILEPATH=${CoreDNSSD_LIBRARY}"
    ${_core_toolchain_args}
  BUILD_BYPRODUCTS "${_core_sdk}/lib/libcorelib.a" "${_core_sdk}/lib/libpresonus_core_allocator.a"
  LOG_CONFIGURE ON LOG_BUILD ON LOG_INSTALL ON)
add_library(PresonusCore::Archive STATIC IMPORTED GLOBAL)
set_target_properties(PresonusCore::Archive PROPERTIES IMPORTED_LOCATION "${_core_sdk}/lib/libcorelib.a")
add_library(PresonusCore::Allocator STATIC IMPORTED GLOBAL)
set_target_properties(PresonusCore::Allocator PROPERTIES IMPORTED_LOCATION "${_core_sdk}/lib/libpresonus_core_allocator.a")
add_library(PresonusCore::Provider INTERFACE IMPORTED GLOBAL)
set_target_properties(PresonusCore::Provider PROPERTIES
  INTERFACE_INCLUDE_DIRECTORIES "${_core_sdk}/include/presonus-core-5"
  INTERFACE_LINK_LIBRARIES "PresonusCore::Archive;PresonusCore::Allocator;PNG::PNG;ZLIB::ZLIB;OpenSSL::SSL;OpenSSL::Crypto;Threads::Threads;CoreDNSSD::CoreDNSSD;m;${CMAKE_DL_LIBS}"
  INTERFACE_COMPILE_DEFINITIONS "PRESONUS_HAS_UPSTREAM_CORE=1;CORE_USE_OPENSSL=1;NDEBUG=1"
  INTERFACE_COMPILE_OPTIONS "-pthread;$<$<COMPILE_LANGUAGE:CXX>:-Ulinux>"
  INTERFACE_COMPILE_FEATURES cxx_std_17)
add_dependencies(PresonusCore::Provider presonus_core_source_project)
# Root packaging should ship the generated SDK/package or build native/ directly.
# Do not export these staging paths as the application's installed interface.
