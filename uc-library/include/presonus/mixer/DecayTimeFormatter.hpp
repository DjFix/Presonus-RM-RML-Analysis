#pragma once
#include "core/public/coreformatter.h"
namespace presonus::mixer {
struct FormatterPortTag {};
} // namespace presonus::mixer
namespace Presonus::Mixer {
class DecayTimeFormatter : public Core::Formatter {
public:
  // Independent construction support; no original constructor/name recovered.
  explicit DecayTimeFormatter(presonus::mixer::FormatterPortTag);
  ~DecayTimeFormatter() override;
  // Modern source overrides; original unencoded return spelling stays pending.
  void print(Data &) const override;
  bool scan(Data &) const override;
};
} // namespace Presonus::Mixer
