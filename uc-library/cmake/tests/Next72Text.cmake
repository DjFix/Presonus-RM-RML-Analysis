# Test subtree only; current72 scope.
add_executable(TextFieldWholeCanonicalReplay tests/recovery/text_field_whole/Replay.cpp)
target_compile_features(TextFieldWholeCanonicalReplay PRIVATE cxx_std_17)
target_compile_options(TextFieldWholeCanonicalReplay PRIVATE -UNDEBUG -Ulinux -O2 -fno-sized-deallocation)
target_link_libraries(TextFieldWholeCanonicalReplay PRIVATE presonus::uc PresonusCore::Provider presonus_private_glibc29)
target_link_options(TextFieldWholeCanonicalReplay PRIVATE -Wl,--wrap=_ZdlPv)
add_test(NAME TextFieldWholeCanonicalReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/text_field_whole/check.py" "replay" "--exe" "$<TARGET_FILE:TextFieldWholeCanonicalReplay>")
set_tests_properties(TextFieldWholeCanonicalReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}" RUN_SERIAL TRUE)
