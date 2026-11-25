#pragma once

#include "core/public/coreformatter.h"

namespace Presonus::UC::Format {

class ChannelNameFormatter : public Core::Formatter {
public:
  ChannelNameFormatter();
  ~ChannelNameFormatter() override;

  void print(Core::Formatter::Data &data) const override;
};

} // namespace Presonus::UC::Format
