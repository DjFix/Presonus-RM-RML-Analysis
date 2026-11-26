#include "presonus/LinkControl.hpp"

#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <string_view>

using Core::Rect;
using namespace Core::Portable;
using Presonus::LinkControl;

namespace {
void *receiver;
const Parameter *primary;
const Parameter *right;
const Bitmap *leftBitmap;
const Bitmap *rightBitmap;

struct Snapshot {
  int role;
  bool leftReferenced;
  bool rightReferenced;
};
Snapshot detachments[4];
int detachCount;
bool deallocated;

void require(bool condition) {
  if (!condition)
    std::abort();
}

class Derived final : public LinkControl {
public:
  using LinkControl::LinkControl;
};

class FixtureControl final : public LinkControl {
public:
  using LinkControl::leftImage;
  using LinkControl::LinkControl;
  using LinkControl::rightImage;
};

void observeDelete(void *address) {
  if (address == receiver) {
    require(!deallocated);
    require(!leftBitmap->isReferenced() && !rightBitmap->isReferenced());
    deallocated = true;
  }
}
} // namespace

extern "C" void realRemove(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *p, IParamObserver *observer) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
void wrapRemove(Parameter *p, IParamObserver *observer) {
  if (receiver && (p == primary || p == right)) {
    require(detachCount < 4);
    detachments[detachCount++] = {p == primary ? 1 : 2,
                                  leftBitmap->isReferenced(),
                                  rightBitmap->isReferenced()};
  }
  realRemove(p, observer);
}

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *value) {
  observeDelete(value);
  __real__ZdlPv(value);
}
extern "C" void __wrap__ZdlPvm(void *value, std::size_t size) {
  observeDelete(value);
  __real__ZdlPvm(value, size);
}

int main(int argc, char **argv) {
  require(argc == 2);
  const std::string_view variant = argv[1];
  ParamInfo info{};
  info.maxValue = 1.f;
  info.defaultValue = 1.f;
  NumericParam a(info), b(info), replacement(info);
  int hasPrimary, side, images, left, top, rightEdge, bottom;
  while (std::cin >> hasPrimary >> side >> images >> left >> top >> rightEdge >>
         bottom) {
    Bitmap imageLeft, imageRight;
    const Rect rect(left, top, rightEdge, bottom);
    auto *parameter = hasPrimary ? &a : nullptr;
    a.setValue(1);
    b.setValue(1);
    if (variant == "provider" || variant == "C1" || variant == "C2") {
      if (variant == "provider") {
        const Control control(rect, parameter);
        require(control.getParameter() == parameter &&
                control.getSize() == rect);
      } else if (variant == "C1") {
        auto *exact = new LinkControl(rect, parameter);
        require(exact->getParameter() == parameter && exact->getSize() == rect);
        require(!exact->isRightSideOfLink() &&
                exact->isLinked() == bool(hasPrimary));
        delete exact;
      } else {
        const Derived base(rect, parameter);
        require(base.getParameter() == parameter && base.getSize() == rect);
        require(!base.isRightSideOfLink() &&
                base.isLinked() == bool(hasPrimary));
      }
      const FixtureControl probe(rect, parameter);
      require(!probe.leftImage.getBitmap() && !probe.rightImage.getBitmap());
      std::cout << hasPrimary << ' ' << left << ' ' << top << ' ' << rightEdge
                << ' ' << bottom << '\n';
      continue;
    }

    auto prepare = [&](LinkControl &control) {
      auto *sideParam = side == 1 ? &a : side >= 2 ? &b : nullptr;
      if (side == 3)
        control.setRightSideParam(&replacement);
      control.setRightSideParam(sideParam);
      control.setRightSideParam(sideParam);
      replacement.setValue(0);
      replacement.setValue(1);
      if (sideParam) {
        require(control.isRightSideOfLink());
        sideParam->setValue(0);
        require(!control.isRightSideOfLink());
        sideParam->setValue(1);
      }
      control.*(&FixtureControl::leftImage) = images & 1 ? &imageLeft : nullptr;
      control.*(&FixtureControl::rightImage) =
          images & 2 ? &imageRight : nullptr;
      primary = parameter;
      right = sideParam;
      leftBitmap = &imageLeft;
      rightBitmap = &imageRight;
      detachCount = 0;
      deallocated = false;
      receiver = &control;
    };
    if (variant == "D0") {
      auto *control = new LinkControl(rect, parameter);
      prepare(*control);
      Control *base = control;
      delete base;
    } else if (variant == "D1") {
      alignas(LinkControl) unsigned char storage[sizeof(LinkControl)];
      auto *control = new (storage) LinkControl(rect, parameter);
      prepare(*control);
      control->~LinkControl();
    } else {
      require(variant == "D2");
      alignas(FixtureControl) unsigned char storage[sizeof(FixtureControl)];
      auto *control = new (storage) FixtureControl(rect, parameter);
      prepare(*control);
      control->~FixtureControl();
    }
    receiver = nullptr;
    require(!imageLeft.isReferenced() && !imageRight.isReferenced());
    a.setValue(0);
    b.setValue(0);
    std::cout << deallocated << ' ' << detachCount;
    for (int i = 0; i < detachCount; ++i) {
      const auto &d = detachments[i];
      std::cout << ' ' << d.role << ' ' << d.leftReferenced << ' '
                << d.rightReferenced;
    }
    std::cout << '\n';
  }

  // A dying source can be the primary, right side, or both. A second source
  // changes after widget destruction to exercise surviving observer cleanup.
  for (int side = 0; side != 3; ++side) {
    a.setValue(0);
    b.setValue(0);
    auto dying = std::make_unique<NumericParam>(info);
    auto control =
        std::make_unique<LinkControl>(Rect(), side != 0 ? dying.get() : &a);
    control->setRightSideParam(side != 1 ? dying.get() : &b);
    dying.reset();
    require(!control->isLinked() && !control->isRightSideOfLink());
    control.reset();
    a.setValue(1);
    a.setValue(0);
    b.setValue(1);
    b.setValue(0);
  }
}
