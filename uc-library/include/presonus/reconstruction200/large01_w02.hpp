#pragma once
#include "presonus/MackieControlModel.hpp"
namespace Presonus {
// Partial abstract interface: no invented panel operations or ARM vtable
// layout.
class IFaderPanel {
public:
  virtual ~IFaderPanel() = 0;
};
} // namespace Presonus
