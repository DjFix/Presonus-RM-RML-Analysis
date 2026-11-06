#pragma once
#include "core/portable/coreparams.h"
#include "presonus/panel/PanelTask.hpp"
// Global original class scope. Inheritance, member names/storage, constructor
// and bool spelling are independent source-port choices, not original ABI.
class LEDNotifyTask final : public Presonus::Panel::PanelTask {
public:
  LEDNotifyTask(Core::Portable::Parameter *parameter, std::uint64_t delay,
                std::uint64_t start)
      : parameter(parameter), delay(delay), start(start) {}
  bool idle() override;
  Core::Portable::Parameter *parameter;
  std::uint64_t delay, start;
};
