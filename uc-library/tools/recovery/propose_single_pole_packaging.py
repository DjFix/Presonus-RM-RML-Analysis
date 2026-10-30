"""Create guarded CMake postimages and a relocated-consumer source; no active edits."""
import hashlib,json
from pathlib import Path
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/'uc-library'
own=lib/'candidates/single-pole-packaging';own.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cmake=(lib/'CMakeLists.txt').read_text();groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text();config=(lib/'cmake/presonus_ucConfig.cmake.in').read_text()
def once(text,old,new):assert text.count(old)==1,old;return text.replace(old,new,1)
provider='''include(cmake/PrivateGlibc29.cmake)
set(PRESONUS_PRIVATE_GLIBC29_OUTPUT "${CMAKE_BINARY_DIR}/private-glibc29-provider")
presonus_add_private_glibc29(presonus_private_glibc29
  REPOSITORY "${PRESONUS_REPOSITORY_ROOT}"
  ARCHIVE "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/glibc-2.9.tar.bz2"
  SIGNATURE "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/glibc-2.9.tar.bz2.sig"
  MANIFEST "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/BUILD-MEMBERS.json"
  GUARD "${CMAKE_CURRENT_SOURCE_DIR}/tools/build_private_glibc29.py"
  PYTHON "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python"
  OUTPUT "${PRESONUS_PRIVATE_GLIBC29_OUTPUT}")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/SinglePole.cpp"
  APPEND PROPERTY COMPILE_DEFINITIONS PRESONUS_DSP_GLIBC29_PRIVATE)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/SinglePole.cpp"
  APPEND PROPERTY COMPILE_OPTIONS
    -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin-expf)
'''
cmake=once(cmake,'include(cmake/CommonObjects.cmake)',provider+'include(cmake/CommonObjects.cmake)')
cmake=once(cmake,'presonus_build_common_objects()','''presonus_build_common_objects()
foreach(_math_role presonus_uc presonus_rm_components)
  target_link_libraries(${_math_role} PUBLIC
    $<BUILD_INTERFACE:presonus_private_glibc29>
    $<INSTALL_INTERFACE:presonus::private_glibc29>)
endforeach()''')
groups=once(groups,'set(PRESONUS_rm_SOURCES\n','set(PRESONUS_rm_SOURCES\n  src/DSP/SinglePole.cpp\n')
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  presonus/dsp/single_pole.hpp\n')
cmake=once(cmake,'    presonus/panel/pot_fader_control.hpp','    presonus/dsp/single_pole.hpp\n    presonus/panel/pot_fader_control.hpp')
test='''  add_executable(dsp_single_pole_tests tests/dsp_single_pole_tests.cpp)
  target_compile_features(dsp_single_pole_tests PRIVATE cxx_std_17)
  target_compile_definitions(dsp_single_pole_tests PRIVATE
    PRESONUS_DSP_GLIBC29_PRIVATE
    PRESONUS_MEASURE_REAL=__real_presonus_glibc29_expf
    PRESONUS_MEASURE_WRAP=__wrap_presonus_glibc29_expf)
  target_compile_options(dsp_single_pole_tests PRIVATE
    -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin-expf)
  target_link_options(dsp_single_pole_tests PRIVATE -Wl,--wrap=presonus_glibc29_expf)
  target_link_libraries(dsp_single_pole_tests PRIVATE presonus::rm_components dl)
  add_test(NAME dsp_single_pole COMMAND dsp_single_pole_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-single-pole/arm-math-vectors.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/dsp-single-pole-differences.txt")
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',test+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
install='''install(FILES "${PRESONUS_PRIVATE_GLIBC29_OUTPUT}/libpresonus_private_glibc29.a"
  DESTINATION lib)
install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/"
  DESTINATION share/presonus_uc/sources/glibc-2.9)
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/tools/build_private_glibc29.py"
              "${CMAKE_CURRENT_SOURCE_DIR}/cmake/PrivateGlibc29.cmake"
  DESTINATION share/presonus_uc/sources/glibc-2.9/build-support)
install(FILES "${PRESONUS_PRIVATE_GLIBC29_OUTPUT}/provider-validation.json"
  DESTINATION share/presonus_uc/sources/glibc-2.9/build-receipts)
'''
cmake=once(cmake,'install(EXPORT presonus_uc_targets',install+'install(EXPORT presonus_uc_targets')
config=once(config,'include("${CMAKE_CURRENT_LIST_DIR}/presonus_uc_targets.cmake")','''get_filename_component(_presonus_uc_package_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
if(NOT TARGET presonus::private_glibc29)
  add_library(presonus::private_glibc29 STATIC IMPORTED)
  set_target_properties(presonus::private_glibc29 PROPERTIES
    IMPORTED_LOCATION "${_presonus_uc_package_prefix}/lib/libpresonus_private_glibc29.a"
    INTERFACE_LINK_LIBRARIES m)
endif()
unset(_presonus_uc_package_prefix)
include("${CMAKE_CURRENT_LIST_DIR}/presonus_uc_targets.cmake")''')
products=[]
for n,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups),('cmake/presonus_ucConfig.cmake.in',config)]:
    dest=own/'postimages'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
    products.append(dict(source=str(dest.relative_to(lib)),target=n,sha256=sha(dest),required_preimage_sha256=sha(lib/n)))
consumer='''#include "presonus/dsp/single_pole.hpp"
#include <cstdint>
#include <cstring>
int main() {
  volatile std::uint32_t frequencyBits = 1036831949U;
  volatile std::uint32_t sampleRateBits = 1174011904U;
  std::uint32_t f = frequencyBits, r = sampleRateBits;
  float frequency, sampleRate;
  std::memcpy(&frequency, &f, sizeof f);
  std::memcpy(&sampleRate, &r, sizeof r);
  float result = presonus::dsp::singlePole(frequency, sampleRate);
  std::uint32_t actual;
  std::memcpy(&actual, &result, sizeof actual);
  return actual == 1065351898U ? 0 : 1;
}
'''
(own/'installed_consumer.cpp').write_text(consumer)
(own/'CONTROLLED-APPLY.json').write_text(json.dumps(dict(products=products,scope='Root proposal: source/provider test and installed GNU source package; no active edits or validation claim',consumer='candidates/single-pole-packaging/installed_consumer.cpp',consumer_sha256=sha(own/'installed_consumer.cpp')),indent=2)+'\n')
print(json.dumps(dict(map=str((own/'CONTROLLED-APPLY.json').relative_to(lib)),map_sha256=sha(own/'CONTROLLED-APPLY.json'),products=3)))
