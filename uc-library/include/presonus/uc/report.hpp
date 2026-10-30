#pragma once

// Original exported symbols have C linkage. These int/const-char-pointer/void
// declarations are explicit source-port choices: C symbol names do not encode
// original parameter, return or callback character qualification declarations.
using UCReportFunction = void (*)(int severity, const char *message);

extern "C" {
void UCSetReportFunction(UCReportFunction function);
void UCReportMessage(int severity, const char *format, ...);
}
