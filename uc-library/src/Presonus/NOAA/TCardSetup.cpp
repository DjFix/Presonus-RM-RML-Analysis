#include "core/system/corethread.h"
#include "presonus/noaa/card.hpp"
namespace Presonus::NOAA {
int TCard::open(const NOAASetupProperty &property) {
  diagnostics_.diagnostic(false, "TCard open", 0, false);
  state_.opaque5c = property.opaque0c;
  state_.observedWord30 = property.observedWord1c;
  state_.observedWord40 = 0;
  state_.opaque2c = property.opaque20;
  int result = TCardSPI::instance().open(property.spiPath);
  Core::Threads::CurrentThread::sleep(1);
  return result;
}
} // namespace Presonus::NOAA
