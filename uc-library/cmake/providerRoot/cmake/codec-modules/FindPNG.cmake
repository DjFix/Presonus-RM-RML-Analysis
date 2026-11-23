# Resolve the unmodified CCL find_package(PNG REQUIRED) against this SDK only.
if(NOT TARGET presonus_png OR NOT TARGET presonus_zlib)
  message(FATAL_ERROR "Pinned codec targets must be defined before configuring CCL")
endif()
set(PNG_FOUND TRUE)
set(PNG_VERSION_STRING "1.6.10")
set(PNG_LIBRARIES presonus_png)
set(PNG_INCLUDE_DIRS "${codec_includes}")
set(ZLIB_LIBRARIES presonus_zlib)
