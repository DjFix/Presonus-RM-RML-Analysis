add_executable(large02_net_adapter01 driver.cpp)
target_link_libraries(large02_net_adapter01 PRIVATE presonus::uc)
target_compile_options(large02_net_adapter01 PRIVATE -fno-lto)
target_link_options(large02_net_adapter01 PRIVATE
  -Wl,--wrap=getifaddrs -Wl,--wrap=gethostname -Wl,--wrap=socket
  -Wl,--wrap=connect -Wl,--wrap=getaddrinfo -Wl,--wrap=gethostbyname
  -Wl,--wrap=getnameinfo)
add_test(NAME large02_net_adapter01
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:large02_net_adapter01>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
