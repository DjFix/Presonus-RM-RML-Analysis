#pragma once

#include "core/public/coreformatter.h"

namespace Presonus::UC::Format {
class Celsius : public Core::IntFormatter {
public:
  // Independent setup with borrowed name and label. The original constructor
  // and object layout remain unresolved.
  Celsius(const char *name, const char *label) : IntFormatter(name, label) {}
  ~Celsius() override;
};
} // namespace Presonus::UC::Format
