#include "presonus/panel/AlertBook.hpp"
#include "core/system/coredebug.h"
#include "core/system/coretime.h"
namespace Presonus::Panel {
void AlertBook::setParamString(const char *text, int tag) {
  if (auto *p = parameters_.getParameterByTag(tag))
    if (auto *string = Core::Portable::StringParam::cast(p))
      string->fromString(text, false);
}
void AlertBook::setup(Page *page, Core::Portable::Parameter *selection,
                      const char *first, const char *second, const char *third,
                      int mode) {
  state_.mode = mode;
  state_.page = page;
  state_.selection = selection;
  if (selection) {
    selection->setValue(1.f, false);
    selection->addObserver(&parameters_);
  }
  setParamString(first, 100);
  setParamString(second, 101);
  setParamString(third, 102);
  // Pinned Linux SystemClock is signed nanoseconds; exact native truncation.
  state_.startedMilliseconds = Core::SystemClock::getTime() / 1000000;
}
void AlertBook::deactivated() {
  Core::DebugPrint("AlertBook::deactivated\n");
  state_.mode = 0;
  if (state_.selection) {
    state_.selection->removeObserver(&parameters_);
    state_.selection->setValue(0.f, false);
    state_.selection = nullptr;
  }
  setParamString("", 100);
  setParamString("", 101);
  setParamString("", 102);
}
} // namespace Presonus::Panel
