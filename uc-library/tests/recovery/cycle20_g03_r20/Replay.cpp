#include "presonus/surface_panel/DigitalPotControl.hpp"

#include <cerrno>
#include <cstdlib>
#include <iostream>
#include <new>
#include <sys/mman.h>
#include <unistd.h>

using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
using Presonus::Panel::Control;
using Presonus::Panel::DigitalPotControl;

namespace {
bool trackNextAllocation = false;
bool trackedUnsizedRelease = false;
void *tracked = nullptr;
std::size_t pageSize = 0;
} // namespace

void *operator new(std::size_t size) {
  if (trackNextAllocation) {
    trackNextAllocation = false;
    if (size != sizeof(DigitalPotControl) || size > pageSize)
      std::abort();
    tracked = mmap(nullptr, pageSize, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (tracked == MAP_FAILED)
      std::abort();
    return tracked;
  }
  if (void *ptr = std::malloc(size ? size : 1))
    return ptr;
  throw std::bad_alloc();
}

void operator delete(void *ptr) noexcept {
  if (ptr && ptr == tracked) {
    if (munmap(ptr, pageSize) != 0)
      std::abort();
    trackedUnsizedRelease = true;
    return;
  }
  std::free(ptr);
}

void operator delete(void *ptr, std::size_t) noexcept {
  if (ptr && ptr == tracked)
    std::abort();
  std::free(ptr);
}

namespace {
class InspectableParam final : public NumericParam {
public:
  explicit InspectableParam(const ParamInfo &info) : NumericParam(info) {}
  bool contains(const void *address) const {
    for (auto entry : observerList)
      if (static_cast<const void *>(entry) == address)
        return true;
    return false;
  }
};

[[gnu::noinline, gnu::noipa]] Control *
constructPot(presonus::panel_binding::DigitalPotState &state) {
  return new DigitalPotControl(state);
}

[[gnu::noinline, gnu::noipa]] void destroyThroughBase(Control *control) {
  delete control;
}

void noDeviceWrite(void *, const std::array<std::uint8_t, 3> &) {
  std::abort();
}

void oldBaseCallback(void *context, Core::Portable::Parameter *, int mode) {
  if (mode == 73)
    ++*static_cast<unsigned *>(context);
}

bool run(int count) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.minValue = -1;
  info.maxValue = 1;
  InspectableParam a(info), b(info), c(info);
  presonus::panel_binding::DigitalPotEndpoint endpoint{nullptr, noDeviceWrite};
  unsigned callbackCount = 0;
  presonus::panel_binding::DigitalPotState state{
      0, 6, &endpoint, &callbackCount, oldBaseCallback};

  trackedUnsizedRelease = false;
  trackNextAllocation = true;
  Control *control = constructPot(state);
  if (static_cast<void *>(control) != tracked || trackNextAllocation ||
      !presonus::panel::ControlAccess::timers().isEmpty())
    return false;
  control->paramChanged(&a, 73);
  if (callbackCount != 1)
    return false;
  if (count)
    control->setParameter(&a, 0);
  if (count == 3) {
    control->setAltParameter(&b);
    control->setTertiaryParameter(&c);
  }
  const void *observer = static_cast<Core::Portable::IParamObserver *>(control);
  if (a.contains(observer) != (count != 0) ||
      b.contains(observer) != (count == 3) ||
      c.contains(observer) != (count == 3))
    return false;

  destroyThroughBase(control);
  unsigned char residency{};
  errno = 0;
  const bool unmapped =
      mincore(tracked, pageSize, &residency) == -1 && errno == ENOMEM;
  tracked = nullptr;
  return trackedUnsizedRelease && unmapped && !a.contains(observer) &&
         !b.contains(observer) && !c.contains(observer) && callbackCount == 1 &&
         state.value == 0 && state.tag == 6 && state.endpoint == &endpoint;
}
} // namespace

int main() {
  const auto systemPageSize = sysconf(_SC_PAGESIZE);
  if (systemPageSize <= 0)
    return 1;
  pageSize = static_cast<std::size_t>(systemPageSize);
  for (int count : {0, 1, 3}) {
    if (!run(count))
      return 1;
    std::cout << count << " observers removed, receiver unmapped\n";
  }
}
