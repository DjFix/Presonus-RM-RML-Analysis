#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstddef>
#include <cstdlib>
#include <iostream>

namespace {
void *tracked = nullptr;
unsigned releases = 0;
unsigned sizedReleases = 0;
void release(void *address, bool sized) {
  if (address == tracked && tracked != nullptr) {
    if (sized)
      ++sizedReleases;
    else
      ++releases;
  }
  std::free(address);
}
} // namespace
void operator delete(void *address) noexcept { release(address, false); }
void operator delete(void *address, std::size_t) noexcept {
  release(address, true);
}

namespace {
using namespace Presonus::Panel;
using namespace Core::Portable;
constexpr ParamInfo parameterInfo =
    PARAM_FLOAT_(1, "pos", 0, 1, 0, 0, "", "", 0, 0, "", "");
class ObservedParameter final : public NumericParam {
public:
  ObservedParameter() : NumericParam(parameterInfo) {}
  int observers() const { return observerList.count(); }
};
[[gnu::noinline]] void destroy(Control *receiver) { delete receiver; }
} // namespace
int main() {
  char letters[] = {'0', 'A', '_'};
  for (int i = 0; i < 3; ++i) {
    releases = 0;
    sizedReleases = 0;
    ObservedParameter main, alt, tertiary;
    auto *receiver = new SevenSegControl(i);
    if (!receiver->setParameter(&main, 0) || !receiver->setAltParameter(&alt) ||
        !receiver->setTertiaryParameter(&tertiary) || main.observers() != 1 ||
        alt.observers() != 1 || tertiary.observers() != 1 ||
        receiver->convertCharToBmp(letters[i], false) == 0)
      return 2;
    Control other(99);
    receiver->startTimer(1.f, 33);
    other.startTimer(1.f, 34);
    if (!receiver->isTimerRunning(33) || !other.isTimerRunning(34))
      return 3;
    tracked = receiver;
    destroy(receiver);
    tracked = nullptr;
    if (sizedReleases != 0)
      return 6;
    if (main.observers() || alt.observers() || tertiary.observers() ||
        !other.isTimerRunning(34) ||
        presonus::panel::ControlAccess::timers().count() != 1)
      return 4;
    std::cout << "ControlD2 delete " << releases << '\n';
  }
}
