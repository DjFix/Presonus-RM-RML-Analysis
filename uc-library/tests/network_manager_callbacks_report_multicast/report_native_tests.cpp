#include "presonus/uc/report.hpp"
#include <cassert>
#include <climits>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
namespace {
int swapHook, formatCalls, callbackCalls, callbackIdentity, severityExpected;
std::string captured;
void capture(int identity, int severity, const char *text) {
  assert(severity == severityExpected);
  assert(text[4095] == 0);
  ++callbackCalls;
  callbackIdentity = identity;
  captured.clear();
  static constexpr char digits[] = "0123456789abcdef";
  for (unsigned i = 0; i < 4096; ++i) {
    auto byte = static_cast<unsigned char>(text[i]);
    captured += digits[byte >> 4];
    captured += digits[byte & 15];
  }
}
void hookA(int severity, const char *text) { capture(1, severity, text); }
void hookB(int severity, const char *text) { capture(2, severity, text); }
} // namespace
extern "C" int __real_vsnprintf(char *, std::size_t, const char *, va_list);
extern "C" int __wrap_vsnprintf(char *text, std::size_t n, const char *format,
                                va_list arguments) {
  ++formatCalls;
  assert(n == 4095);
  // Fixture-only initialization makes untouched buffer tail observable and
  // fully defined; actual source owns4096 bytes and forces the last byte zero.
  std::memset(text, 0xa5, 4096);
  int result = __real_vsnprintf(text, n, format, arguments);
  if (swapHook)
    UCSetReportFunction(swapHook == 1 ? hookA : hookB);
  return result;
}
extern "C" int __real___vsnprintf_chk(char *, std::size_t, int, std::size_t,
                                      const char *, va_list);
extern "C" int __wrap___vsnprintf_chk(char *text, std::size_t n, int flags,
                                      std::size_t capacity, const char *format,
                                      va_list arguments) {
  ++formatCalls;
  assert(n == 4095 && capacity >= 4096);
  std::memset(text, 0xa5, 4096);
  int result =
      __real___vsnprintf_chk(text, n, flags, capacity, format, arguments);
  if (swapHook)
    UCSetReportFunction(swapHook == 1 ? hookA : hookB);
  return result;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  int severity, initial, swap, kind, expectedFormatCalls, expectedIdentity;
  std::string expectedBuffer;
  unsigned cases = 0;
  while (input >> severity >> initial >> swap >> kind >> expectedFormatCalls >>
         expectedIdentity >> expectedBuffer) {
    severityExpected = severity;
    swapHook = swap;
    formatCalls = callbackCalls = callbackIdentity = 0;
    captured.clear();
    UCSetReportFunction(initial == 0 ? nullptr : initial == 1 ? hookA : hookB);
    if (kind < 7) {
      const unsigned lengths[] = {0, 1, 4093, 4094, 4095, 4096, 5000};
      std::string payload(lengths[kind], 'x');
      UCReportMessage(severity, "%s", payload.c_str());
    } else if (kind == 7) {
      UCReportMessage(severity, "%d/%u/%08x/%s/%c/%%", -1234567, UINT_MAX,
                      0xabcdefU, "label", 'Q');
    } else if (kind == 8) {
      UCReportMessage(severity, "%*.*f", 14, 3, 1.234567);
    } else {
      assert(initial == 0);
      UCReportMessage(severity, reinterpret_cast<const char *>(1));
    }
    assert(formatCalls == expectedFormatCalls);
    assert(callbackIdentity == expectedIdentity);
    assert(callbackCalls == (initial != 0));
    assert(captured == (expectedBuffer == "-" ? "" : expectedBuffer));
    ++cases;
  }
  UCSetReportFunction(nullptr);
  std::cout << "{\"passed\":true,\"cases\":" << cases << "}\n";
}
