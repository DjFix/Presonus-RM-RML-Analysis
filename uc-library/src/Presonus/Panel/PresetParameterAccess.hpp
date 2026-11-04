#pragma once
#include "core/portable/corecomponent.h"
#include <cmath>
#include <stdexcept>

// Shared internal source-port validation helpers; no recovered original API.
namespace {
inline Core::Portable::Parameter &
required(const Core::Portable::Component &component, int tag) {
  auto *p = component.getParameterByTag(tag);
  if (!p)
    throw std::logic_error("missing preset parameter binding");
  return *p;
}
inline int integerValue(Core::Portable::Parameter &p) {
  const float v = p.getValue();
  if (!std::isfinite(v) || v < -2147483648.f || v >= 2147483648.f)
    throw std::domain_error("preset integer domain");
  return static_cast<int>(v);
}
} // namespace
