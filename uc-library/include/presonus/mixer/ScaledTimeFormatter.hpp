#pragma once
#include "core/public/coreformatter.h"
namespace presonus::mixer {
struct ScaledTimeFormatterPortTag {};
} // namespace presonus::mixer
namespace Presonus::Mixer {
class ScaledTimeFormatter : public Core::Formatter {
public:
  // Independent construction support; no original constructor/name recovered.
  explicit ScaledTimeFormatter(presonus::mixer::ScaledTimeFormatterPortTag);
  ~ScaledTimeFormatter() override;
  // Modern source overrides; original unencoded return spelling stays pending.
  void print(Data &) const override;
  bool scan(Data &) const override;
};
} // namespace Presonus::Mixer
