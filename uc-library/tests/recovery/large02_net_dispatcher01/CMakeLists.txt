# Root adds EventDispatcherLifetime.cpp to the common OBJECT partition once.
add_executable(large02_net_dispatcher01 driver.cpp)
target_link_libraries(large02_net_dispatcher01 PRIVATE presonus_cs18_components)
target_link_options(large02_net_dispatcher01 PRIVATE
  -Wl,--wrap=_Znam -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm
  -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm
  -Wl,--wrap=pthread_mutex_init -Wl,--wrap=pthread_mutex_destroy
  -Wl,--wrap=pthread_mutex_lock -Wl,--wrap=pthread_mutex_unlock)
add_test(NAME large02_net_dispatcher01
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:large02_net_dispatcher01>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
