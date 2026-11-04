add_executable(stabilized01_uart driver.cpp)
target_link_libraries(stabilized01_uart PRIVATE presonus_uc)
target_compile_features(stabilized01_uart PRIVATE cxx_std_20)
target_link_options(stabilized01_uart PRIVATE
  "-Wl,--wrap=open,--wrap=close,--wrap=read,--wrap=write,--wrap=ioctl,--wrap=tcgetattr,--wrap=tcsetattr,--wrap=cfsetspeed,--wrap=cfmakeraw,--wrap=fcntl,--wrap=clock_gettime,--wrap=printf,--wrap=__printf_chk")
add_test(NAME stabilized01_uart_native_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --driver "$<TARGET_FILE:stabilized01_uart>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
