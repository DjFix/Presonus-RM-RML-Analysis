add_executable(reconstruction200_large02_w01 driver.cpp)
target_link_libraries(reconstruction200_large02_w01 PRIVATE presonus_cs18_components)
target_sources(reconstruction200_large02_w01 PRIVATE $<TARGET_OBJECTS:panel_hal_core_rtti>)
target_compile_options(reconstruction200_large02_w01 PRIVATE -O3 -DNDEBUG -frtti -fno-lto -fno-fast-math -ffp-contract=off)
target_link_options(reconstruction200_large02_w01 PRIVATE
  -Wl,--wrap=_ZN8Presonus10DelayTimer5resetEv
  -Wl,--wrap=_ZNK4Core8Portable9ParamList5byTagEi
  -Wl,--wrap=_ZN8Presonus12MappingTable15setControlColorEPKcS2_)
add_test(NAME reconstruction200_large02_w01
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:reconstruction200_large02_w01>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
