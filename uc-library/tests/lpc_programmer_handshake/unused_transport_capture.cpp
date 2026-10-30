// Test-only fail-closed boundaries for unused transport members in the same
// object.
extern "C" int __wrap_open(const char *, int, ...) { __builtin_trap(); }
extern "C" int __wrap_tcgetattr(int, void *) { __builtin_trap(); }
extern "C" int __wrap_tcsetattr(int, int, const void *) { __builtin_trap(); }
extern "C" int __wrap_tcflush(int, int) { __builtin_trap(); }
extern "C" void __wrap_cfmakeraw(void *) { __builtin_trap(); }
extern "C" int __wrap_close(int) { __builtin_trap(); }
extern "C" void unusedDebug(const char *,
                            ...) asm("__wrap__ZN4Core11DebugPrintfEPKcz");
extern "C" void unusedDebug(const char *, ...) { __builtin_trap(); }
