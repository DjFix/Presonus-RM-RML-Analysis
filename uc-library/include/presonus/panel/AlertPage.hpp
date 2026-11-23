#pragma once

#include "presonus/panel/Page.hpp"

namespace Presonus::Panel {

// The inherited constructors initialize the portable Page state. Only the
// original deleting destructor is selected for recovery.
class AlertPage : public Page {
public:
  using Page::Page;
  ~AlertPage() override;
};

} // namespace Presonus::Panel
