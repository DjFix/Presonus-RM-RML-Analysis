#pragma once
#include "core/public/corestringbuffer.h"
namespace Presonus::Surface {
// Native method appends to an incoming initialized 64-byte string. Portable
// owned state uses pinned CCL, without asserting original inheritance/layout.
class PageParam {
public:
  explicit PageParam(const char *initial = "") : text_(initial) {}
  void init(const char *, const char *);
  const char *c_str() const { return text_.str(); }

private:
  Core::CStringBuffer<64> text_;
};
} // namespace Presonus::Surface
