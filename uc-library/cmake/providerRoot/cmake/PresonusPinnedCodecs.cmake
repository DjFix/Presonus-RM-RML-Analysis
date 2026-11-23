function(presonus_check_codec_source directory expected_commit)
  execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${directory}" rev-parse HEAD
    OUTPUT_VARIABLE commit OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
  if(NOT commit STREQUAL expected_commit)
    message(FATAL_ERROR "Expected pinned checkout ${expected_commit} in ${directory}, found ${commit}")
  endif()
  execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${directory}" status --porcelain --untracked-files=all
    OUTPUT_VARIABLE changes OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
  if(changes)
    message(FATAL_ERROR "Pinned checkout must be clean: ${directory}\n${changes}")
  endif()
endfunction()

set(zlib_source "${PRESONUS_CODEC_SOURCE_ROOT}/zlib-reference-1.2.11")
set(png_source "${PRESONUS_CODEC_SOURCE_ROOT}/libpng-reference-1.6.10")
presonus_check_codec_source("${zlib_source}" cacf7f1d4e3d44d871b605da3b647f07d718623f)
presonus_check_codec_source("${png_source}" 4df37bfa4f79dcd742fca6155e26b8d37b591c30)
if(CMAKE_SCRIPT_MODE_FILE)
  return()
endif()

include(CheckFunctionExists)
include(CheckIncludeFile)
include(CheckTypeSize)
include(CMakePushCheckState)

# A normal incremental build may recompile a touched vendor file without running
# configure. Recheck both checkouts before either archive can be rebuilt.
add_custom_target(presonus_codec_source_check
  COMMAND "${CMAKE_COMMAND}" "-DGIT_EXECUTABLE=${GIT_EXECUTABLE}"
    "-DPRESONUS_CODEC_SOURCE_ROOT=${PRESONUS_CODEC_SOURCE_ROOT}"
    -P "${CMAKE_CURRENT_LIST_FILE}"
  VERBATIM)

# The release CMake script renames its checked-in zconf.h in an out-of-tree
# build. Stage the release headers and generate the configured header in binary
# space while compiling the unmodified upstream C sources from the checkout.
set(codec_includes "${CMAKE_CURRENT_BINARY_DIR}/codec-includes")
cmake_push_check_state(RESET)
set(CMAKE_REQUIRED_DEFINITIONS -D_LARGEFILE64_SOURCE=1)
check_type_size(off64_t PRESONUS_OFF64_T)
cmake_pop_check_state()
check_function_exists(fseeko PRESONUS_HAVE_FSEEKO)
check_include_file(unistd.h Z_HAVE_UNISTD_H)
configure_file("${zlib_source}/zconf.h.cmakein" "${codec_includes}/zconf.h" @ONLY)
configure_file("${zlib_source}/zlib.h" "${codec_includes}/zlib.h" COPYONLY)
configure_file("${png_source}/png.h" "${codec_includes}/png.h" COPYONLY)
configure_file("${png_source}/pngconf.h" "${codec_includes}/pngconf.h" COPYONLY)
configure_file("${png_source}/scripts/pnglibconf.h.prebuilt" "${codec_includes}/pnglibconf.h" COPYONLY)

# These are the portable static source lists in the two release CMake files.
set(zlib_sources adler32.c compress.c crc32.c deflate.c gzclose.c gzlib.c
  gzread.c gzwrite.c inflate.c infback.c inftrees.c inffast.c trees.c uncompr.c zutil.c)
set(png_sources png.c pngerror.c pngget.c pngmem.c pngpread.c pngread.c pngrio.c
  pngrtran.c pngrutil.c pngset.c pngtrans.c pngwio.c pngwrite.c pngwtran.c pngwutil.c)
list(TRANSFORM zlib_sources PREPEND "${zlib_source}/")
list(TRANSFORM png_sources PREPEND "${png_source}/")
add_library(presonus_zlib STATIC ${zlib_sources})
add_library(presonus_png STATIC ${png_sources})
set_target_properties(presonus_zlib PROPERTIES EXPORT_NAME Zlib)
set_target_properties(presonus_png PROPERTIES EXPORT_NAME Png)
set(presonus_codec_include_dir "${CMAKE_INSTALL_INCLUDEDIR}/presonus-core-codecs")
foreach(codec IN ITEMS presonus_zlib presonus_png)
  add_dependencies(${codec} presonus_codec_source_check)
  set_target_properties(${codec} PROPERTIES POSITION_INDEPENDENT_CODE ON)
  target_include_directories(${codec} PUBLIC
    "$<BUILD_INTERFACE:${codec_includes}>"
    "$<INSTALL_INTERFACE:${presonus_codec_include_dir}>")
endforeach()
# zlib's own quoted includes find the release zconf.h first. Keep its
# feature definitions consistent with the generated public zconf.h.
if(Z_HAVE_UNISTD_H)
  target_compile_definitions(presonus_zlib PRIVATE HAVE_UNISTD_H)
endif()
if(HAVE_PRESONUS_OFF64_T)
  target_compile_definitions(presonus_zlib PRIVATE _LARGEFILE64_SOURCE=1)
endif()
if(NOT PRESONUS_HAVE_FSEEKO)
  target_compile_definitions(presonus_zlib PRIVATE NO_FSEEKO)
endif()
# This build uses the portable C implementation on all Linux hosts.
target_compile_definitions(presonus_png PRIVATE PNG_ARM_NEON_OPT=0)
target_link_libraries(presonus_png PUBLIC presonus_zlib m)

install(TARGETS presonus_png presonus_zlib EXPORT PresonusCoreTargets
  ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(FILES "${codec_includes}/zlib.h" "${codec_includes}/zconf.h"
  "${codec_includes}/png.h" "${codec_includes}/pngconf.h" "${codec_includes}/pnglibconf.h"
  DESTINATION "${presonus_codec_include_dir}")
install(FILES "${png_source}/LICENSE"
  DESTINATION "${CMAKE_INSTALL_DATADIR}/presonus-core-5/upstream/libpng")
install(FILES "${zlib_source}/README"
  DESTINATION "${CMAKE_INSTALL_DATADIR}/presonus-core-5/upstream/zlib")
