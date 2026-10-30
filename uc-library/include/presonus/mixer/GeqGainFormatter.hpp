#pragma once
#include "core/public/coreformatter.h"
namespace presonus::mixer {
struct GeqGainFormatterPortTag {};
} // namespace presonus::mixer
namespace Presonus::Mixer {
class GeqGainFormatter : public Core::Formatter {
public:
  // Independent construction support; no original constructor/name recovered.
  explicit GeqGainFormatter(presonus::mixer::GeqGainFormatterPortTag);
  ~GeqGainFormatter() override;
  // Modern source overrides; original unencoded return spelling stays pending.
  void print(Data &) const override;
  bool scan(Data &) const override;
};
} // namespace Presonus::Mixer
