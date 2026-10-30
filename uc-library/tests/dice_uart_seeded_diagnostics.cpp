// Test-only linker boundary: retain new UART lifetime diagnostics on stderr
// while old ARM stdout witnesses keep their original byte-for-byte contract.
// Actual CCL DebugPrintf provider smoke must not link this capture helper.
#include <cstdarg>
#include <cstdio>

extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  va_list args;
  va_start(args, format);
  std::vfprintf(stderr, format, args);
  va_end(args);
}
