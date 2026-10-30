#pragma once
#include "core/public/coreformatter.h"
namespace presonus::mixer {
struct FeedbackFormatterPortTag {};
} // namespace presonus::mixer
namespace Presonus::Mixer {
class FeedbackFormatter : public Core::Formatter {
public:
  // Independent construction support; no original constructor/name recovered.
  explicit FeedbackFormatter(presonus::mixer::FeedbackFormatterPortTag);
  ~FeedbackFormatter() override;
  // Modern source overrides; original unencoded return spelling stays pending.
  void print(Data &) const override;
  bool scan(Data &) const override;
};
} // namespace Presonus::Mixer
