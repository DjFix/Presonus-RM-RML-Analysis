#include "presonus/PanControl.hpp"

#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <string_view>
#include <vector>

namespace {
using Core::Portable::IParamObserver;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::View;
using Presonus::PanControl;

class TrackedParameter : public NumericParam {
public:
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
class TrackedBitmap : public Core::Portable::Bitmap {
public:
  int count() const { return useCount; }
};
class Peer : public IParamObserver {
public:
  void *castTo(Core::Portable::ITypedObject::TypeID) override {
    return nullptr;
  }
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kChanged)
      ++notifications;
  }
  int notifications = 0;
};
class DerivedPan final : public PanControl {
public:
  ~DerivedPan() override;
};
DerivedPan::~DerivedPan() = default;

const void *receiver = nullptr;
IParamObserver *observer = nullptr;
std::array<TrackedParameter *, 7> providers{};
const TrackedBitmap *bitmap = nullptr;
std::vector<unsigned> events;
std::vector<unsigned> setup;
bool tearingDown = false;
bool recordSetup = false;
bool hasPrimary = false;

void observe(Parameter *p, IParamObserver *who, bool adding) {
  if (who != observer)
    return;
  for (std::size_t index = 0; index < providers.size(); ++index) {
    if (p != providers[index])
      continue;
    if (tearingDown) {
      if (adding || (index == 6 && (!hasPrimary || bitmap->count() != 2)))
        std::abort();
      events.push_back(index == 6 ? 7 : static_cast<unsigned>(index + 1));
    } else if (recordSetup && index != 6) {
      setup.push_back(static_cast<unsigned>(index + (adding ? 11 : 1)));
    }
    return;
  }
  std::abort();
}

void release(const void *address) {
  if (address == receiver) {
    if (!tearingDown || bitmap->count() != 3 - hasPrimary)
      std::abort();
    events.push_back(8);
  }
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);

extern "C" void __wrap__ZdlPv(void *address) {
  release(address);
  __real__ZdlPv(address);
}
extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) {
  release(address);
  __real__ZdlPvm(address, size);
}
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *who) {
  observe(p, who, false);
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      p, who);
}
extern "C" void
__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *who) {
  observe(p, who, true);
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(p,
                                                                         who);
}

namespace {
[[gnu::noipa]] void virtualDelete(View *view) { delete view; }
[[gnu::noipa]] void destroyDerived(DerivedPan *pan) { pan->~DerivedPan(); }

bool exercise(std::string_view mode, unsigned mask, bool primary,
              unsigned replaced, unsigned destroyed, unsigned borrowCase) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.maxValue = 1.f;
  std::array<std::unique_ptr<TrackedParameter>, 7> parameters;
  for (std::size_t i = 0; i < parameters.size(); ++i) {
    parameters[i] = std::make_unique<TrackedParameter>(info);
    providers[i] = parameters[i].get();
  }
  TrackedBitmap image;
  image.use();
  image.use();
  image.use();

  alignas(DerivedPan) unsigned char storage[sizeof(DerivedPan)];
  DerivedPan *derived = mode == "base" ? new (storage) DerivedPan : nullptr;
  PanControl *pan = derived              ? derived
                    : mode == "deleting" ? new PanControl
                                         : new (storage) PanControl;
  receiver = pan;
  observer = static_cast<IParamObserver *>(pan);
  bitmap = &image;
  hasPrimary = primary;
  events.clear();
  setup.clear();
  if (primary) {
    image.unuse();
    pan->setImage(Core::Portable::BitmapReference(&image));
    pan->setParameter(providers[6]);
  }
  if (image.count() != 3)
    return false;
  constexpr std::array setters{
      &PanControl::setStereoParam, &PanControl::setLinkParam,
      &PanControl::setChannelNumberParam, &PanControl::setRightSideParam,
      &PanControl::setStereoPanParam};
  recordSetup = true;
  for (unsigned i = 0; i < setters.size(); ++i)
    if (mask & (1u << i))
      (pan->*setters[i])(providers[i]);
  if (replaced)
    (pan->*setters[replaced - 1])(providers[5]);
  recordSetup = false;

  if (destroyed) {
    parameters[destroyed - 1].reset();
    providers[destroyed - 1] = nullptr;
    if (pan->panParameters()[destroyed - 1])
      return false;
  }
  if (borrowCase) {
    pan->bindPanParameters({providers[0], nullptr, nullptr, nullptr, nullptr});
    pan->setStereoParam(providers[0]);
    if (providers[0]->observers() != 1)
      return false;
    pan->setLinkParam(providers[0]);
    if (providers[0]->observers() != 2)
      return false;
    pan->bindPanParameters(
        {providers[0], providers[1], nullptr, nullptr, nullptr});
    if (providers[0]->observers() || providers[1]->observers())
      return false;
    // One borrowed provider outlives the widget and the other does not.
    parameters[0].reset();
    providers[0] = nullptr;
  }
  Peer peer;
  unsigned survivors = 0;
  for (auto &param : parameters) {
    if (!param)
      continue;
    param->addObserver(&peer);
    ++survivors;
  }

  tearingDown = true;
  if (derived)
    destroyDerived(derived);
  else if (mode == "deleting")
    virtualDelete(pan);
  else
    pan->PanControl::~PanControl();
  tearingDown = false;
  receiver = observer = nullptr;
  bitmap = nullptr;
  const auto finalBitmapCount = image.count();
  if (finalBitmapCount != 3 - primary)
    return false;
  for (int i = 0; i < finalBitmapCount; ++i)
    image.unuse();

  for (auto &param : parameters) {
    if (!param)
      continue;
    if (param->observers() != 1)
      return false;
    param->changed();
    param->removeObserver(&peer);
  }
  if (peer.notifications != static_cast<int>(survivors))
    return false;
  std::cout << finalBitmapCount;
  for (auto value : events)
    std::cout << ' ' << value;
  std::cout << " 0";
  for (auto value : setup)
    std::cout << ' ' << value;
  std::cout << '\n';
  return true;
}
} // namespace

int main(int argc, char **argv) {
  const std::string_view mode = argc == 2 ? argv[1] : "";
  if (mode != "complete" && mode != "base" && mode != "deleting")
    return 2;
  unsigned mask, replaced, destroyed, borrowed;
  bool primary;
  while (std::cin >> mask >> primary >> replaced >> destroyed >> borrowed)
    if (!exercise(mode, mask, primary, replaced, destroyed, borrowed))
      return 3;
  return std::cin.eof() ? 0 : 4;
}
