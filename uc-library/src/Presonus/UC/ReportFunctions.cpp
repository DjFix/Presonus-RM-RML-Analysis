#include "presonus/uc/report.hpp"
#include <cstdarg>
#include <cstdio>

// Exact original local symbol identity. Native pointer size differs from the
// original ARM32 four-byte SHT_NOBITS slot; binary layout is not claimed.
static UCReportFunction theReportFunction = nullptr;

extern "C" void UCSetReportFunction(UCReportFunction function) {
  theReportFunction = function;
}

extern "C" void UCReportMessage(int severity, const char *format, ...) {
  if (!theReportFunction)
    return;
  char text[4096];
  va_list arguments;
  va_start(arguments, format);
  std::vsnprintf(text, 4095, format, arguments);
  va_end(arguments);
  text[4095] = 0;
  // The original reloads the global slot after formatting. Do not cache the
  // callback across vsnprintf. Concurrent mutation has no verified contract.
  theReportFunction(severity, text);
}
