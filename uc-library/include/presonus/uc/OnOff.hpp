#pragma once
#include "core/public/coreformatter.h"
namespace Presonus::UC::Format {
// Genuine app class, actual pinned CCL base. ARM layout/RTTI ABI is not
// claimed. Ordinary returns follow the actual CCL virtual interface; original
// unencoded return declarations remain unresolved. Labels are borrowed for this
// lifetime.
class OnOff : public Core::Formatter {
public:
  OnOff(const char *name, const char *on, const char *off);
  ~OnOff() override;
  void print(Core::Formatter::Data &data) const override;
  bool scan(Core::Formatter::Data &data) const override;

private:
  const char *on_;
  const char *off_;
};
} // namespace Presonus::UC::Format
