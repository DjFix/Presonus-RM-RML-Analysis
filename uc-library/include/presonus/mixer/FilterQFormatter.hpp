#pragma once
#include "core/public/coreformatter.h"
namespace presonus::mixer {
struct FilterQFormatterPortTag {};
} // namespace presonus::mixer
namespace Presonus::Mixer {
class FilterQFormatter : public Core::Formatter {
public:
  // Independent construction support; no original constructor/name recovered.
  explicit FilterQFormatter(presonus::mixer::FilterQFormatterPortTag);
  ~FilterQFormatter() override;
  // Modern source overrides; original unencoded return spelling stays pending.
  void print(Data &) const override;
  bool scan(Data &) const override;
};
} // namespace Presonus::Mixer
