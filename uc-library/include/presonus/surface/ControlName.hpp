#pragma once
#include "core/public/corestringbuffer.h"
namespace Presonus::Surface {
// Portable CString32 composition; original inheritance/layout remain
// unresolved.
class ControlName {
public:
  ControlName(const char *, int);
  const char *str() const { return value_.str(); }

private:
  Core::CString32 value_;
};
} // namespace Presonus::Surface
