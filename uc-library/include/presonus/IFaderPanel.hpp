#pragma once
#include "presonus/MackieControlModel.hpp"
namespace Presonus {
// Partial source-port interface. Local updates are an optional portable
// capability with original operations, independent of the ARM vtable layout.
class IFaderPanel {
public:
  class LocalUpdates;
  virtual ~IFaderPanel() = 0;
  virtual LocalUpdates *localUpdates() { return nullptr; }
};
class IFaderPanel::LocalUpdates : public IFaderPanel {
public:
  LocalUpdates *localUpdates() final { return this; }
  virtual void updateLedState(int, int) = 0;
  virtual void updateFader(int, float) = 0;
  virtual void updateMeter(int, float) = 0;
  virtual void updateValueBar(int, int, float, bool) = 0;
  virtual void updateTextDisplay(int, const char *, int) = 0;
};
} // namespace Presonus
